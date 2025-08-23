#!/usr/bin/env node

/**
 * Claude Flow Quick Test Script
 * Use this to verify Claude Flow is working on any project
 */

console.log('🚀 Claude Flow Quick Test Script');
console.log('================================');

// Test 1: Check if MCP server is installed
console.log('\n📋 Test 1: MCP Server Status');
console.log('Run this command in terminal:');
console.log('claude mcp status claude-flow');

// Test 2: Basic functionality test
console.log('\n📋 Test 2: Basic Functionality');
console.log('Copy this EXACT message into Claude Code:');
console.log('---');
console.log('Initialize a simple swarm with one researcher agent to test Claude Flow functionality.');
console.log('---');

// Test 3: Expected results
console.log('\n📋 Test 3: Expected Results');
console.log('✅ Should see: Task tool with subagent_type');
console.log('✅ Should see: Swarm ID generated');
console.log('✅ Should see: Agent spawned successfully');
console.log('❌ Should NOT see: Hook command errors');

// Test 4: Troubleshooting
console.log('\n📋 Test 4: If Tests Fail');
console.log('1. Check CLAUDE.md exists in project root');
console.log('2. Verify MCP server: claude mcp list');
console.log('3. Remove hook references from CLAUDE.md');
console.log('4. Use only MCP tools via Task tool');

console.log('\n🎯 Quick Success Check:');
console.log('Working = Multiple Task tools in single message');
console.log('Broken = Hook command errors or sequential messages');