export async function GET(request, {params}) {
  const {path} = await params;
  if (!['health','runs','answers','retrieve'].includes(path[0])) return Response.json({detail:'Unknown endpoint'}, {status:404});
  try {
    const result = await fetch(`${process.env.ACE_API_URL || 'http://127.0.0.1:8060'}/${path.map(encodeURIComponent).join('/')}`, {cache:'no-store', signal:AbortSignal.timeout(30000)});
    return new Response(await result.text(), {status:result.status, headers:{'Content-Type':'application/json'}});
  } catch {return Response.json({detail:'Evidence service unavailable. Start the local API.'}, {status:503})}
}
