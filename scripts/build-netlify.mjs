import {cp,rm,mkdir} from 'node:fs/promises';
await rm('dist',{recursive:true,force:true});await mkdir('dist',{recursive:true});await cp('static','dist',{recursive:true});
console.log('Netlify UI ready. Serverless APIs use Netlify Database and Blobs; no external Python API required.');
