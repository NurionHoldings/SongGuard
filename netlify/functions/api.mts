import type {Context,Config} from '@netlify/functions';
import {getStore} from '@netlify/blobs';
import {getUser,login,logout,verifyRequestOrigin} from '@netlify/identity';
import {database,ensureSchema} from './_shared/db.mjs';
import {createHandler} from './_shared/api.mjs';
export default async (req:Request,context:Context)=>{
  const env=(key:string)=>Netlify.env.get(key);
  let pool;
  try { return await createHandler({env,pool:()=>{pool??=database(env);return pool},ensure:ensureSchema,
    blobs:()=>getStore({name:'song-guard-evidence',consistency:'strong'}),
    verifyOrigin:verifyRequestOrigin,identityUser:getUser,identityLogin:login,identityLogout:logout
  })(req,context); } finally { if(pool) await pool.end(); }
};
export const config:Config={path:['/api/*','/health']};
