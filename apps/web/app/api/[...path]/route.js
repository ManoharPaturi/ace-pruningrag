const api = () => process.env.ACE_API_URL || 'http://127.0.0.1:8060';
export async function GET(request, {params}) {
  const {path} = await params;
  if (!['health','runs','answers','retrieve','live'].includes(path[0])) return Response.json({detail:'Unknown endpoint'}, {status:404});
  try {
    const result = await fetch(`${api()}/${path.map(encodeURIComponent).join('/')}`, {cache:'no-store', signal:AbortSignal.timeout(30000)});
    return new Response(await result.text(), {status:result.status, headers:{'Content-Type':'application/json'}});
  } catch {return Response.json({detail:'Evidence service unavailable. Start the local API.'}, {status:503})}
}
export async function POST(request, {params}) {
  const {path} = await params;
  if (path.length!==3 || path[0]!=='live' || path[1]!=='generate') return Response.json({detail:'Unknown endpoint'}, {status:404});
  const origin=request.headers.get('Origin');
  if(origin){try{const parsed=new URL(origin);if(!['http:','https:'].includes(parsed.protocol)||parsed.host!==request.headers.get('host'))return Response.json({detail:'Request origin differs'},{status:403});}catch{return Response.json({detail:'Invalid origin'},{status:403});}}
  const key=request.headers.get('Idempotency-Key');
  if(!key) return Response.json({detail:'Request identity required'}, {status:400});
  try {
    const result=await fetch(`${api()}/${path.map(encodeURIComponent).join('/')}`, {method:'POST',headers:{'Idempotency-Key':key},cache:'no-store',signal:AbortSignal.timeout(30000)});
    return new Response(await result.text(), {status:result.status,headers:{'Content-Type':'application/json'}});
  } catch {return Response.json({detail:'Submission response unavailable. Retry this same request.'},{status:503})}
}
