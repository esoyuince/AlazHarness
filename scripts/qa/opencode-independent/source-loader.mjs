/** Independent QA loader: unchanged target source; explicit fixture ports, no app bootstrap. */
import {registerHooks,stripTypeScriptTypes} from 'node:module';
import {readFileSync,existsSync} from 'node:fs';
import {dirname,resolve,sep} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
const here=dirname(fileURLToPath(import.meta.url));
const cfg=JSON.parse(readFileSync(process.env.ALAZ_OC_QA_CONFIG,'utf8'));
const source=resolve(cfg.source),effect=resolve(cfg.dependency_home,'node_modules/effect/dist');
const sourceURL=pathToFileURL(source+sep).href;
const fixture=pathToFileURL(resolve(here,'ports.mjs')).href;
const permission=pathToFileURL(resolve(source,'packages/core/src/permission.ts')).href;
const feed=pathToFileURL(resolve(source,'packages/server/src/event-feed.ts')).href;
const allowedPermissionPorts=new Set(['@opencode/util/effect/app-node','./bus.js','./location.js','./agent.js','./session/error.js','./session/schema.js','./session/store.js','./permission/saved.js','./plugin/hooks.js']);
const hashes={
 [permission]:'9a7ad5b124652a635048a0ffb3878df20b3c510703296c741c5db8333c87a54c',
 [feed]:'6988d912bc8be3fb2a32e18fb5c45509f0b4295ace1d8c9c00a66df9c7acae5c',
};
globalThis.__ocQaLoads=[];
registerHooks({
 resolve(specifier,context,next){
  if(specifier==='effect')return {url:pathToFileURL(resolve(effect,'index.js')).href,shortCircuit:true};
  if(specifier.startsWith('effect/')){
   const sub=specifier.slice(7);const file=sub==='http-api'?resolve(effect,sub,'index.js'):resolve(effect,sub+'.js');
   return {url:pathToFileURL(file).href,shortCircuit:true};
  }
  if(context.parentURL===permission && allowedPermissionPorts.has(specifier))return {url:fixture,shortCircuit:true};
  if(context.parentURL===feed && specifier==='@opencode/core/bus')return {url:fixture,shortCircuit:true};
  if(specifier.startsWith('@opencode/')){
   const m=/^@opencode\/(schema|protocol)\/(.+)$/.exec(specifier);
   if(!m)throw new Error('Unapproved application module: '+specifier);
   const file=resolve(source,'packages',m[1],'src',m[2]+'.ts');
   return {url:pathToFileURL(file).href,shortCircuit:true};
  }
  if(context.parentURL?.startsWith(sourceURL) && specifier.startsWith('.')){
   const path=resolve(dirname(fileURLToPath(context.parentURL)),specifier);
   const candidates=[path,path.endsWith('.js')?path.slice(0,-3)+'.ts':path+'.ts'];
   const found=candidates.find(p=>existsSync(p));
   if(found)return {url:pathToFileURL(found).href,shortCircuit:true};
  }
  return next(specifier,context);
 },
 load(url,context,next){
  if(url.startsWith(sourceURL)){
   const data=readFileSync(fileURLToPath(url)),sha=createHash('sha256').update(data).digest('hex');
   if(hashes[url] && hashes[url]!==sha)throw new Error('Pinned target drift');
   globalThis.__ocQaLoads.push({url,sha256:sha});
   if(url.endsWith('.ts'))return {format:'module',source:stripTypeScriptTypes(data.toString('utf8'),{mode:'transform',sourceUrl:url}),shortCircuit:true};
  }
  return next(url,context);
 }
});
