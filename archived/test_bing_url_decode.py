#!/usr/bin/env python3
"""
Test decoding Bing redirect URLs to extract actual business URLs
"""

import base64
import urllib.parse as urlparse_module
import json

def decode_bing_redirect_url(bing_url):
    """Decode Bing redirect URL to get actual destination URL"""
    try:
        # Check if it's a Bing redirect URL
        if 'bing.com/ck/a' not in bing_url:
            return bing_url
        
        # Extract the 'u=' parameter
        if '&u=' in bing_url:
            parts = bing_url.split('&u=')
            if len(parts) > 1:
                encoded_url = parts[1].split('&')[0]
                
                # The URL appears to be base64 encoded but with 'a1' prefix
                if encoded_url.startswith('a1'):
                    encoded_url = encoded_url[2:]  # Remove 'a1' prefix
                
                try:
                    # Decode base64
                    decoded_bytes = base64.b64decode(encoded_url + '==')  # Add padding
                    decoded_url = decoded_bytes.decode('utf-8')
                    return decoded_url
                except:
                    pass
        
        return bing_url
        
    except Exception as e:
        print(f"Error decoding URL: {e}")
        return bing_url

def test_url_decoding():
    """Test decoding with actual URLs from the search results"""
    
    # Load the search results
    with open("debug_lawyer_search_results.json", "r", encoding="utf-8") as f:
        results = json.load(f)
    
    print("Testing URL decoding for Bing redirect URLs:")
    print("=" * 60)
    
    decoded_results = []
    
    for i, result in enumerate(results):
        original_url = result['url']
        decoded_url = decode_bing_redirect_url(original_url)
        
        print(f"Result {i+1}: {result['title'][:50]}...")
        print(f"  Original: {original_url[:80]}...")
        print(f"  Decoded:  {decoded_url}")
        
        # Parse the decoded URL to get domain
        if decoded_url != original_url:
            try:
                parsed = urlparse_module.urlparse(decoded_url)
                domain = parsed.netloc
                print(f"  Domain:   {domain}")
                
                # Update result with decoded info
                result_copy = result.copy()
                result_copy['url'] = decoded_url
                result_copy['domain'] = domain
                result_copy['is_decoded'] = True
                decoded_results.append(result_copy)
                
            except Exception as e:
                print(f"  Error parsing decoded URL: {e}")
                result_copy = result.copy()
                result_copy['is_decoded'] = False
                decoded_results.append(result_copy)
        else:
            result_copy = result.copy()
            result_copy['is_decoded'] = False
            decoded_results.append(result_copy)
        
        print()
    
    # Save decoded results
    with open("debug_lawyer_search_decoded.json", "w", encoding="utf-8") as f:
        json.dump(decoded_results, f, indent=2)
    
    print("=" * 60)
    print("Summary:")
    decoded_count = sum(1 for r in decoded_results if r['is_decoded'])
    print(f"Total results: {len(decoded_results)}")
    print(f"Successfully decoded: {decoded_count}")
    
    if decoded_count > 0:
        print("\nDecoded business URLs:")
        for r in decoded_results:
            if r['is_decoded']:
                print(f"  {r['domain']} -> {r['url']}")

if __name__ == "__main__":
    test_url_decoding()