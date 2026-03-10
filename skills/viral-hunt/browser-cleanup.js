#!/usr/bin/env node
/**
 * Browser Tab Cleanup Script
 * Closes all tabs except a whitelist of essential URLs
 * Run before viral hunt to free memory
 */

const CDP = require('chrome-remote-interface');

const KEEP_PATTERNS = [
  /^about:blank$/,
  /tiktok\.com\/@viralfarm\.ai$/,  // Keep TikTok profile for posting
];

async function cleanup() {
  const client = await CDP({ port: 18800 });
  const { Target } = client;
  
  const targets = await Target.getTargets();
  const pages = targets.targetInfos.filter(t => t.type === 'page');
  
  console.log(`Found ${pages.length} tabs`);
  
  let closed = 0;
  for (const page of pages) {
    const shouldKeep = KEEP_PATTERNS.some(p => p.test(page.url));
    
    if (!shouldKeep && page.url !== 'about:blank') {
      try {
        await Target.closeTarget({ targetId: page.targetId });
        console.log(`Closed: ${page.url.substring(0, 60)}...`);
        closed++;
      } catch (e) {
        console.error(`Failed to close ${page.targetId}: ${e.message}`);
      }
    }
  }
  
  console.log(`Closed ${closed} tabs`);
  await client.close();
}

cleanup().catch(console.error);
