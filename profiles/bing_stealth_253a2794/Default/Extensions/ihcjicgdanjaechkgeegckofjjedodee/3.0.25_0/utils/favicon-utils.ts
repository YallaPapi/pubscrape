/**
 * Utilities for fetching and processing favicons
 */
import { md5 } from 'js-md5';

/**
 * Cache for favicon hashes to avoid re-fetching and re-hashing
 */
export const faviconHashCache = new Map<string, string>();

let useLogging = false;

//@ts-ignore
if (ENVIRONMENT == "development" && typeof window !== "undefined") {
  useLogging = true;
}

/**
 * Fetches a favicon from a website and calculates its MD5 hash from the binary data
 * @param url The URL of the website to fetch the favicon from
 * @returns A Promise that resolves to the MD5 hash of the favicon's binary data or null if not found
 */
export async function getFaviconHash(url: string): Promise<string | null> {
  try {
    // Check cache first
    if (faviconHashCache.has(url)) {
      return faviconHashCache.get(url) || null;
    }

    // Extract origin from URL
    const {origin} = new URL(url);
    
    // Try different favicon sources
    const faviconSources: string[] = [];
    
    // Try to find favicon in link tags
    try {
      // Look for link tags in the document
      const linkTags = document.querySelectorAll('link[rel*="icon"]');
      if (linkTags.length > 0) {
        for (const tag of Array.from(linkTags)) {
          const href = tag.getAttribute('href');
          if (href) {
            // Convert relative URLs to absolute
            if (href.startsWith('/')) {
              faviconSources.unshift(`${origin}${href}`);
            } else if (!href.startsWith('http')) {
              faviconSources.unshift(`${origin}/${href}`);
            } else {
              faviconSources.unshift(href);
            }
          }
        }
      }
    } catch (error) {
      useLogging && console.debug('Error parsing document for favicon links:', error);
    }

    !faviconSources.length && faviconSources.push(`${origin}/favicon.ico`);  // HTTPs default
    // Try each favicon source
    for (const faviconUrl of faviconSources) {
      try {
        const response = await fetch(faviconUrl, { method: 'GET' });
        if (response.ok) {
          // Get the binary data of the favicon for hashing
          const blob = await response.blob();
          const arrayBuffer = await blob.arrayBuffer();
          const uint8Array = new Uint8Array(arrayBuffer);
          
          // Calculate MD5 hash of the binary data directly
          const hash = md5(uint8Array);
          
          // Cache the result
          faviconHashCache.set(url, hash);
          
          return hash;
        }
      } catch (error) {
        useLogging && console.debug(`Failed to fetch favicon from ${faviconUrl}:`, error);
      }
    }
    
    return null;
  } catch (error) {
    useLogging && console.debug('Error getting favicon hash:', error);
    return null;
  }
}