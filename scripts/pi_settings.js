#!/usr/bin/env node
// Strict JSON transforms used only during deployment; never stores credentials.
const fs = require('node:fs');
const path = require('node:path');
const { fileURLToPath } = require('node:url');
const { isDeepStrictEqual } = require('node:util');

const common = [
  '@juicesharp/rpiv-ask-user-question',
  'pi-subagents', 'pi-web-access', 'pi-extmgr',
];
const planners = ['@plannotator/pi-extension', 'pi-plan'];
const context7 = { url: 'https://mcp.context7.com/mcp', exposure: 'direct' };
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);

function readConfig(filename) {
  if (!fs.existsSync(filename)) return {};
  let value;
  try { value = JSON.parse(fs.readFileSync(filename, 'utf8').replace(/^\uFEFF/, '')); }
  catch { throw new Error(`${filename}: 无效 JSON，请先修复；原文件未被合并工具修改`); }
  if (!object(value)) throw new Error(`${filename}: 配置必须是 JSON 对象`);
  return value;
}

function packageName(entry) {
  const source = typeof entry === 'string' ? entry : entry?.source;
  if (typeof source !== 'string') throw new Error('packages 条目必须是字符串或带 source 的对象');
  return /^npm:((?:@[^/]+\/)?[^@]+)(?:@.*)?$/.exec(source)?.[1];
}

function settings(filename, mode) {
  const value = readConfig(filename);
  if (value.packages !== undefined && !Array.isArray(value.packages)) {
    throw new Error(`${filename}: packages 必须是数组`);
  }
  const active = mode === 'gui' ? planners[0] : planners[1];
  const inactive = mode === 'gui' ? planners[1] : planners[0];
  const required = [...common, active];
  const seen = new Set();
  const packages = [];
  for (const entry of value.packages || []) {
    const name = packageName(entry);
    // Retire the old managed package without deleting its cached files.
    if (name === '@juicesharp/rpiv-todo') continue;
    if (!required.includes(name) && name !== inactive) { packages.push(entry); continue; }
    if (seen.has(name)) continue;
    seen.add(name);
    if (name === inactive) {
      packages.push({ source: `npm:${name}`, extensions: [], skills: [], prompts: [], themes: [] });
    } else if (name === active || typeof entry === 'string') {
      packages.push(`npm:${name}`);
    } else {
      packages.push({ ...entry, source: `npm:${name}` });
    }
  }
  for (const name of required) {
    if (!seen.has(name)) packages.push(`npm:${name}`);
  }
  // A manually installed inactive package may not yet be registered in settings.
  if (!seen.has(inactive) && fs.existsSync(path.join(path.dirname(filename), 'npm/node_modules', inactive, 'package.json'))) {
    packages.push({ source: `npm:${inactive}`, extensions: [], skills: [], prompts: [], themes: [] });
  }
  return { original: value, merged: { ...value, packages } };
}

function validateReferences(value, repo, base) {
  const inside = filename => filename === repo || filename.startsWith(`${repo}/`);
  if (typeof value === 'string') {
    let filename = value;
    if (filename.startsWith('file://')) filename = fileURLToPath(filename);
    if (filename.startsWith('~/')) filename = path.join(process.env.HOME, filename.slice(2));
    let referenced = value === repo || value.includes(`${repo}/`);
    if (path.isAbsolute(filename) || filename.startsWith('./') || filename.startsWith('../')) {
      filename = path.resolve(base, filename);
      referenced ||= inside(filename);
      if (fs.existsSync(filename)) referenced ||= inside(fs.realpathSync(filename));
    }
    if (referenced) throw new Error('Pi 配置仍引用本仓库，请先把本机资源迁至仓库外再部署');
  }
  if (value && typeof value === 'object') {
    for (const item of Object.values(value)) validateReferences(item, repo, base);
  }
}

try {
  const [action, filename, argument, extra] = process.argv.slice(2);
  if (action === 'resolve') {
    let value = filename;
    if (value.startsWith('file://')) value = fileURLToPath(value);
    if (value === '~') value = extra;
    else if (value.startsWith('~/')) value = path.join(extra, value.slice(2));
    console.log(path.resolve(argument, value));
  } else if (action === 'settings-check' || action === 'settings-merge') {
    if (!['gui', 'headless'].includes(argument)) throw new Error('未知 Pi 环境');
    const { original, merged } = settings(filename, argument);
    if (extra) validateReferences(merged, extra, path.dirname(filename));
    console.log(action === 'settings-check'
      ? (isDeepStrictEqual(original, merged) ? 'unchanged' : 'changed')
      : JSON.stringify(merged, null, 2));
  } else if (action === 'mcp-check') {
    const value = readConfig(filename);
    if (value.mcpServers !== undefined && !object(value.mcpServers)) throw new Error('mcpServers 必须是对象');
    if (argument) validateReferences(value, argument, path.dirname(filename));
    console.log(isDeepStrictEqual(value.mcpServers?.context7, context7) ? 'unchanged' : 'changed');
  } else if (action === 'managed') {
    const value = readConfig(path.join(filename, 'install/managed-install.json'));
    if (value.kind !== 'pi-managed-install' || value.layout !== 'releases-v1') {
      throw new Error('已有 Pi 不是可接管的官方管理安装，请先手动使用官网 curl 迁移，或使用 --skip-pi');
    }
  } else {
    throw new Error('未知 Pi 配置操作');
  }
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
