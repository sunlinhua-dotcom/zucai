// Cloudflare Pages Function：/api/jqc
// 服务端代理中国体育彩票官方接口（4场进球 gameNo=94），解决浏览器跨域，归一化为前端易用的 JSON。
// 上游：webapi.sporttery.cn ... lotteryDrawNum(期号) / lotteryDrawResult(开奖，空格分隔，3+ 记为 "3＋")
const UPSTREAM = 'https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=94&provinceId=0&pageSize=30&isVerify=1&pageNo=1';
const HDRS = {
  'content-type': 'application/json; charset=utf-8',
  'access-control-allow-origin': '*',
  'cache-control': 'public, max-age=600, s-maxage=600',
};
function toDigit(s){ s=String(s).trim(); if(!s) return null; if(s[0]==='3') return 3; const n=parseInt(s,10); return isNaN(n)?null:Math.min(n,3); }

export async function onRequestGet(){
  try{
    const ctl = new AbortController(); const timer = setTimeout(()=>ctl.abort(), 8000);
    let r;
    try{
      r = await fetch(UPSTREAM, { signal: ctl.signal, headers:{
        'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17 Safari/605.1.15',
        'Referer':'https://www.sporttery.cn/', 'Accept':'application/json',
      }, cf:{ cacheTtl:600, cacheEverything:true } });
    } finally { clearTimeout(timer); }
    if(!r.ok) throw new Error('upstream '+r.status);
    const j = await r.json();
    const list = (j && j.value && j.value.list) || [];
    const results = list.map(it=>{
      const digits = String(it.lotteryDrawResult||'').trim().split(/\s+/).map(toDigit);
      return { issue:String(it.lotteryDrawNum||''), digits, sales:it.totalSaleAmount||null };
    }).filter(x=> x.issue && x.digits.length===8 && x.digits.every(d=>d!==null));
    const issues = results.map(x=>x.issue);
    return new Response(JSON.stringify({ ok:true, source:'sporttery', game:'4场进球', gameNo:94, latest:issues[0]||null, issues, results }), {headers:HDRS});
  }catch(e){
    return new Response(JSON.stringify({ ok:false, error:String(e&&e.message||e) }), {headers:HDRS, status:200});
  }
}
