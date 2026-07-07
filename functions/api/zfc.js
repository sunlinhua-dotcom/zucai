// Cloudflare Pages Function：/api/zfc
// 服务端代理中国体育彩票官方接口（14场胜负彩 gameNo=90），解决浏览器跨域，归一化为前端易用的 JSON。
// 两路上游：
//   1) getHistoryPageListV1 —— 历史开奖（lotteryDrawResult: 14 个 3/1/0 = 胜/平/负；matchList 含主客队名）
//   2) getFootBallMatchV1   —— 当前在售期的赛程 + 欧赔(h/d/a)，用于实时预测
const HIST = 'https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=90&provinceId=0&pageSize=30&isVerify=1&pageNo=';
const UPCOMING = 'https://webapi.sporttery.cn/gateway/lottery/getFootBallMatchV1.qry?param=90,0&isFsl=1';
const HDRS = {
  'content-type': 'application/json; charset=utf-8',
  'access-control-allow-origin': '*',
  'cache-control': 'public, max-age=600, s-maxage=600',
};
const FETCH_HDRS = {
  'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17 Safari/605.1.15',
  'Referer':'https://www.sporttery.cn/', 'Accept':'application/json', 'Accept-Language':'zh-CN,zh;q=0.9',
};
const M = {'3':'W','1':'P','0':'L'};
const clean = s => String(s||'').replace(/\s+/g,'');
const fnum = x => { const n=parseFloat(x); return isFinite(n)?n:null; };

async function getJSON(url){
  const ctl=new AbortController(); const timer=setTimeout(()=>ctl.abort(),8000);
  try{ const r=await fetch(url,{signal:ctl.signal,headers:FETCH_HDRS,cf:{cacheTtl:600,cacheEverything:true}});
    if(!r.ok) throw new Error('upstream '+r.status); return await r.json(); }
  finally{ clearTimeout(timer); }
}

export async function onRequestGet(){
  try{
    // —— 历史开奖：抓 2 页（~60 期）——
    const recent=[], results=[];
    for(let p=1;p<=2;p++){
      let j; try{ j=await getJSON(HIST+p); }catch(e){ break; }
      const list=(j&&j.value&&j.value.list)||[];
      for(const it of list){
        const issue=String(it.lotteryDrawNum||'').trim();
        const parts=String(it.lotteryDrawResult||'').trim().split(/\s+/);
        if(!(issue && parts.length===14 && parts.every(x=>x==='0'||x==='1'||x==='3'))) continue;
        const wpl=parts.map(x=>M[x]).join('');
        recent.push([issue, wpl]);
        const ml=it.matchList||[];
        if(ml.length===14){ results.push([issue, ml.map((m,i)=>[clean(m.masterTeamName),clean(m.guestTeamName),M[parts[i]]])]); }
      }
    }
    recent.sort((a,b)=>(+a[0])-(+b[0])); results.sort((a,b)=>(+a[0])-(+b[0]));

    // —— 在售期赛程 + 欧赔 ——
    let upcoming=null;
    try{
      const u=await getJSON(UPCOMING);
      const sfc=u&&u.value&&u.value.sfcMatch;
      if(sfc&&Array.isArray(sfc.matchList)&&sfc.matchList.length){
        upcoming={ issue:String(sfc.lotteryDrawNum||''), drawTime:String(sfc.estimateDrawTime||'').slice(0,10),
          saleEnd:String(sfc.lotterySaleEndtime||'').slice(0,16),
          matches:sfc.matchList.map(m=>({ no:m.matchNum, h:clean(m.masterTeamName), a:clean(m.guestTeamName),
            oh:fnum(m.h), od:fnum(m.d), oa:fnum(m.a), league:m.matchName||'' })) };
      }
    }catch(e){}

    const latest = recent.length? recent[recent.length-1][0] : null;
    return new Response(JSON.stringify({ ok:true, source:'sporttery', game:'胜负彩', gameNo:90, latest, recent, results, upcoming }), {headers:HDRS});
  }catch(e){
    return new Response(JSON.stringify({ ok:false, error:String(e&&e.message||e) }), {headers:HDRS, status:200});
  }
}
