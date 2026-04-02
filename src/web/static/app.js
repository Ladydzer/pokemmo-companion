const TC={Normal:'#A8A77A',Fire:'#EE8130',Water:'#6390F0',Electric:'#F7D02C',Grass:'#7AC74C',Ice:'#96D9D6',Fighting:'#C22E28',Poison:'#A33EA1',Ground:'#E2BF65',Flying:'#A98FF3',Psychic:'#F95587',Bug:'#A6B91A',Rock:'#B6A136',Ghost:'#735797',Dragon:'#6F35FC',Dark:'#705746',Steel:'#B7B7CE'};
const SC={hp:'#78C850',attack:'#F08030',defense:'#F8D030',sp_attack:'#6890F0',sp_defense:'#78C850',speed:'#F85888'};
const TFR={Normal:'Normal',Fire:'Feu',Water:'Eau',Electric:'Electrik',Grass:'Plante',Ice:'Glace',Fighting:'Combat',Poison:'Poison',Ground:'Sol',Flying:'Vol',Psychic:'Psy',Bug:'Insecte',Rock:'Roche',Ghost:'Spectre',Dragon:'Dragon',Dark:'Tenebres',Steel:'Acier'};
const TEN=Object.fromEntries(Object.entries(TFR).map(([en,fr])=>[fr,en])); // FR->EN reverse
const tfr=t=>TFR[t]||t; // Translate type to FR
const pill=t=>`<span class="type-pill" style="background:${TC[t]||'#888'}">${tfr(t)}</span>`;
const spr=n=>`https://play.pokemonshowdown.com/sprites/ani/${n.toLowerCase().replace(/[^a-z0-9]/g,'')}.gif`;
// Fallback: add onerror to img tags that use spr()
document.addEventListener('error',e=>{if(e.target.tagName==='IMG'&&e.target.src.includes('showdown')){const id=e.target.dataset?.id;if(id)e.target.src=`/sprite/${id}`;}},true);

function go(p){
    // Smooth transition: fade out current, fade in new
    const current=document.querySelector('.page:not(.hidden)');
    if(current){current.style.opacity='0';current.style.transform='translateY(8px)';}
    setTimeout(()=>{
        document.querySelectorAll('.page').forEach(x=>{x.classList.add('hidden');x.style.opacity='';x.style.transform='';});
        const el=document.getElementById('page-'+p);
        if(el){el.classList.remove('hidden');el.style.opacity='0';el.style.transform='translateY(8px)';
            requestAnimationFrame(()=>{el.style.transition='opacity 0.3s ease, transform 0.3s ease';el.style.opacity='1';el.style.transform='translateY(0)';});
        }
        document.querySelectorAll('.nav-btn').forEach(b=>b.classList.remove('active'));
        document.querySelector(`[data-page="${p}"]`)?.classList.add('active');
        // Lazy-load page data on first visit
        if(p==='pokedex'&&!window._dx)loadDex();
        if(p==='collection'&&!window._cl)loadCol();
        if(p==='shiny'&&!window._sh){window._sh=true;ocrLoadRegions();loadOptStats();shinyUpdate();loadHordeSummary();loadHordes();calcSS();}
        if(p==='combat'&&!window._cb){window._cb=true;rTm();loadChart();}
        if(p==='equipe'&&!window._eq){window._eq=true;rTm();}
        if(p==='guide'&&!window._gu){window._gu=true;loadGuide('Kanto');}
        if(p==='evtrain'&&!window._ev){window._ev=true;loadEVTracker();calcBreed();renderNatures(NATURES);}
        if(p==='ivcalc'){}// IV calc page is static, no lazy load needed
        if(p==='options'&&!window._op){window._op=true;ocrLoadRegions();runDiagnostic();}
        if(p==='routes'&&!window._rt){window._rt=true;loadRoutes();}
    }, current?150:0);
}

// Live detection polling (overlay → web sync)
let _lastLiveRoute='';
let _routeStartTime=0;
let _routeHistory=[];
setInterval(async()=>{
    if(document.getElementById('page-dashboard').classList.contains('hidden'))return;
    try{
        const d=await fetch('/api/ocr/latest').then(r=>r.json());
        const dot=document.getElementById('live-dot');
        if(d.active){
            dot.style.background='#76ff03';dot.classList.add('live-pulse');
            document.getElementById('live-route').textContent=d.route||'---';
            document.getElementById('live-region').textContent=d.region?`(${d.region})`:'';
            document.getElementById('live-age').textContent=d.age_seconds>=0?`${d.age_seconds.toFixed(0)}s`:'';
            // Update dashboard route card too
            if(d.route)document.getElementById('loc-route').textContent=d.route;
            // Update route timer
            if(_routeStartTime>0){
                const secs=Math.floor((Date.now()-_routeStartTime)/1000);
                const m=Math.floor(secs/60),s=secs%60;
                document.getElementById('live-timer').textContent=`${m}:${String(s).padStart(2,'0')}`;
            }
            // Auto-load spawns when route changes
            if(d.route&&d.route!==_lastLiveRoute){
                // Save previous route to history
                if(_lastLiveRoute&&_routeStartTime>0){
                    const dur=Math.floor((Date.now()-_routeStartTime)/1000);
                    _routeHistory.unshift({name:_lastLiveRoute,duration:dur});
                    if(_routeHistory.length>5)_routeHistory.pop();
                    const hl=document.getElementById('live-history');
                    const hll=document.getElementById('live-history-list');
                    if(hl&&hll&&_routeHistory.length){
                        hl.classList.remove('hidden');
                        hll.innerHTML=_routeHistory.map(h=>{
                            const m=Math.floor(h.duration/60),s=h.duration%60;
                            return`<span class="text-[10px] px-2 py-0.5 rounded" style="background:rgba(0,229,255,0.06)">${h.name} <span class="mono" style="color:#ffd740">${m}:${String(s).padStart(2,'0')}</span></span>`;
                        }).join('');
                    }
                }
                _routeStartTime=Date.now();
                _lastLiveRoute=d.route;
                try{
                    const spawns=await fetch(`/api/spawns/${encodeURIComponent(d.route)}`).then(r=>r.json());
                    const el=document.getElementById('live-spawns');
                    if(el&&Array.isArray(spawns)&&spawns.length){
                        el.innerHTML=spawns.slice(0,6).map(s=>`<span class="text-xs px-2 py-0.5 rounded" style="background:${TC[s.type1]||'#888'}20;color:${TC[s.type1]||'#ccc'}">${s.pokemon_name} ${s.rate?.toFixed(0)||'?'}%</span>`).join(' ');
                        el.classList.remove('hidden');
                    }else if(el){el.classList.add('hidden');}
                }catch(e){}
            }
            // Battle state
            const bp=document.getElementById('live-battle');
            if(d.in_battle&&d.opponent){
                bp.classList.remove('hidden');
                document.getElementById('live-opponent').textContent=d.opponent;
                document.getElementById('live-level').textContent=d.level?`Niv.${d.level}`:'';
                document.getElementById('live-types').innerHTML=(d.opponent_types||[]).map(t=>pill(t)).join(' ');
            }else{bp.classList.add('hidden');}
        }else{
            dot.style.background='#616161';dot.classList.remove('live-pulse');
            document.getElementById('live-age').textContent='offline';
        }
    }catch(e){}
},2000);

async function loadDash(){
    try{
        const s=await fetch('/api/stats').then(r=>r.json());
        const spot=await fetch('/api/spotlight').then(r=>r.json());
        if(spot.id){
            document.getElementById('hero-sprite').src=spr(spot.name);
            document.getElementById('hero-name').textContent=spot.name.toUpperCase();
            document.getElementById('hero-num').textContent=String(spot.id).padStart(3,'0');
            document.getElementById('hero-types').innerHTML=pill(spot.type1)+(spot.type2?' '+pill(spot.type2):'');
            if(spot.location) document.getElementById('hero-sprite').title=spot.location.route_name;
            const stats=[['PV',spot.hp,'hp'],['ATTAQUE',spot.attack,'attack'],['VITESSE',spot.speed,'speed']];
            document.getElementById('hero-stat-bars').innerHTML=stats.map(([l,v,k])=>`
                <div><p class="text-xs text-gray-500 mb-1">${l}</p>
                <p class="text-xl font-black text-white">${v}</p>
                <div class="stat-track mt-1"><div class="stat-fill" style="width:${v/255*100}%;background:${SC[k]}"></div></div></div>
            `).join('');
        }
    }catch(e){console.error(e);}

    // Default spawns (Route 1 Kanto)
    try{
        const sp=await fetch('/api/spawns/Route%201?region=Kanto').then(r=>r.json());
        if(Array.isArray(sp)&&sp.length){
            const sl=document.getElementById('spawns-list');
            sl.innerHTML=sp.slice(0,6).map(s=>`<div class="spawn-row"><img src="${spr(s.pokemon_name)}" data-id="${s.pokemon_id}" class="w-8 h-8 sprite-hover"><span class="font-semibold text-white text-sm flex-1">${s.pokemon_name}</span>${pill(s.type1)}<div class="stat-track w-20"><div class="stat-fill bg-neon-green" style="width:${Math.min(s.rate,100)}%"></div></div><span class="mono text-xs text-gray-400">${s.rate.toFixed(0)}%</span><span class="text-xs text-gray-500">Lv.${s.level_min}-${s.level_max}</span></div>`).join('');
            document.getElementById('spawn-subtitle').textContent='Route 1 (Kanto)';
            document.getElementById('loc-route').textContent='ROUTE 1';
        }
    }catch(e){}

    // Collection count for dashboard
    const caught=JSON.parse(localStorage.getItem('caught')||'[]');
    updateColCount(caught.length);

    // Recent favorites on dashboard
    const favs=JSON.parse(localStorage.getItem('favorites')||'[]');
    if(favs.length){
        const panel=document.getElementById('dash-favs');
        const list=document.getElementById('dash-favs-list');
        panel.classList.remove('hidden');
        const recent=favs.slice(-6).reverse(); // last 6, newest first
        try{
            const favData=await Promise.all(recent.map(id=>fetch(`/api/pokemon/${id}`).then(r=>r.json()).catch(()=>null)));
            list.innerHTML=favData.filter(Boolean).map(p=>`<div class="text-center cursor-pointer" onclick="go('pokedex');setTimeout(()=>showP(${p.id}),300)" title="${p.name_fr||p.name}">
                <img src="${spr(p.name)}" class="w-10 h-10 mx-auto sprite-hover" style="border-bottom:2px solid ${TC[p.type1]||'#888'}">
                <p class="text-[9px] text-white mt-1">${(p.name_fr||p.name).slice(0,8)}</p>
            </div>`).join('');
        }catch(e){}
    }

    // Player stats
    const shD=JSON.parse(localStorage.getItem('shiny_data')||'{}');
    const noteCount=Object.keys(localStorage).filter(k=>k.startsWith('note_')).length;
    const el2=id=>document.getElementById(id);
    if(el2('ps-enc'))el2('ps-enc').textContent=(shD.total||0).toLocaleString();
    if(el2('ps-shi'))el2('ps-shi').textContent=shD.shinies||0;
    if(el2('ps-col'))el2('ps-col').textContent=caught.length;
    if(el2('ps-fav'))el2('ps-fav').textContent=favs.length;
    if(el2('ps-not'))el2('ps-not').textContent=noteCount;
}

async function loadDex(){
    window._dx=true;
    // Show skeleton loading
    const g=document.getElementById('dex-grid');
    if(g)g.innerHTML=Array(12).fill('<div class="skeleton" style="height:120px"></div>').join('');
    try{
        const pk=await fetch('/api/pokemon/all').then(r=>r.json());
        if(!Array.isArray(pk))return;
        window._pk=pk;
        const f=document.getElementById('type-filters');
        f.innerHTML=`<button onclick="fDex('')" class="type-pill cursor-pointer" style="background:#00e5ff">TOUS</button> <button onclick="filterFavs()" class="type-pill cursor-pointer" style="background:#ffd740;color:#000">★ FAV</button> `;
        Object.keys(TC).forEach(t=>{f.innerHTML+=`<button onclick="fDex('${t}')" class="type-pill cursor-pointer" style="background:${TC[t]}">${tfr(t).slice(0,3)}</button> `;});
        rDex(pk);
        document.getElementById('dex-search').addEventListener('input',e=>{
            const q=e.target.value.toLowerCase();
            if(q.length<2){rDex(window._pk);return;}
            rDex(window._pk.filter(p=>p.name.toLowerCase().includes(q)||(p.name_fr||'').toLowerCase().includes(q)||String(p.id).includes(q)||p.type1.toLowerCase().includes(q)||(p.type2||'').toLowerCase().includes(q)));
        });
    }catch(e){console.error(e);}
}
function fDex(t){window._typeFilter=t||'';applyDexFilters();}
function applyDexFilters(){
    let list=window._pk||[];
    // Type filter
    const tf=window._typeFilter||'';
    if(tf)list=list.filter(p=>p.type1===tf||p.type2===tf);
    // Region filter
    const region=document.getElementById('dex-region')?.value;
    if(region){const[s,e]=region.split('-').map(Number);list=list.filter(p=>p.id>=s&&p.id<=e);}
    // Sort
    const sort=document.getElementById('dex-sort')?.value||'id';
    if(sort==='name')list=[...list].sort((a,b)=>a.name.localeCompare(b.name));
    else if(sort==='bst')list=[...list].sort((a,b)=>(b.hp+b.attack+b.defense+b.sp_attack+b.sp_defense+b.speed)-(a.hp+a.attack+a.defense+a.sp_attack+a.sp_defense+a.speed));
    else if(['hp','attack','defense','sp_attack','sp_defense','speed'].includes(sort))list=[...list].sort((a,b)=>(b[sort]||0)-(a[sort]||0));
    // Count
    const cnt=document.getElementById('dex-count');
    if(cnt)cnt.textContent=`${list.length} Pokemon`;
    rDex(list);
}

let _dexPage=0;const _DEX_PAGE=60;let _dexList=[];
function rDex(list){
    _dexList=list;_dexPage=0;
    const g=document.getElementById('dex-grid');g.innerHTML='';
    document.getElementById('dex-detail').classList.add('hidden');g.classList.remove('hidden');
    _appendDex();
}
function _appendDex(){
    const g=document.getElementById('dex-grid');
    const start=_dexPage*_DEX_PAGE;const batch=_dexList.slice(start,start+_DEX_PAGE);
    if(!batch.length)return;
    const frag=document.createDocumentFragment();
    batch.forEach(p=>{
        const t2=p.type2?' / '+tfr(p.type2):'';
        const d=document.createElement('div');d.className='dex-card';d.onclick=()=>showP(p.id);
        const tc1=TC[p.type1]||'#888';
        d.style.borderBottom='3px solid '+tc1;
        d.style.background=`linear-gradient(135deg, ${tc1}15 0%, rgba(13,17,23,0.6) 60%)`;
        d.title=(p.name_fr||p.name)+' ('+tfr(p.type1)+t2+')';
        const typePills=`<span class="inline-block text-[8px] font-bold px-1.5 py-0.5 rounded-full mt-1 cursor-pointer hover:brightness-125" style="background:${tc1}40;color:${tc1}" onclick="event.stopPropagation();fDex('${p.type1}')">${tfr(p.type1)}</span>`+(p.type2?` <span class="inline-block text-[8px] font-bold px-1.5 py-0.5 rounded-full mt-1 cursor-pointer hover:brightness-125" style="background:${TC[p.type2]||'#888'}40;color:${TC[p.type2]||'#888'}" onclick="event.stopPropagation();fDex('${p.type2}')">${tfr(p.type2)}</span>`:'');
        d.innerHTML=`<img src="${spr(p.name)}" data-id="${p.id}" class="w-14 h-14 mx-auto sprite-hover" loading="lazy" alt="${p.name_fr||p.name}">
            <p class="text-[11px] font-semibold text-white mt-1">${p.name_fr||p.name}</p>
            <p class="text-[9px] text-gray-600">#${String(p.id).padStart(3,'0')}</p>
            <div>${typePills}</div>`;
        frag.appendChild(d);
    });
    g.appendChild(frag);_dexPage++;
    // Show load more button
    let btn=document.getElementById('dex-load-more');
    if(start+_DEX_PAGE<_dexList.length){
        if(!btn){btn=document.createElement('button');btn.id='dex-load-more';btn.className='btn btn-ghost btn-sm text-neon-cyan w-full mt-4';btn.onclick=()=>_appendDex();g.parentNode.appendChild(btn);}
        btn.textContent=`Charger plus (${_dexList.length-start-_DEX_PAGE} restants)`;btn.classList.remove('hidden');
    }else if(btn){btn.classList.add('hidden');}
}

async function showP(id){
    try{
        const[p,locs,evos]=await Promise.all([fetch(`/api/pokemon/${id}`).then(r=>r.json()),fetch(`/api/pokemon/${id}/locations`).then(r=>r.json()),fetch(`/api/pokemon/${id}/evolutions`).then(r=>r.json())]);
        const bst=p.hp+p.attack+p.defense+p.sp_attack+p.sp_defense+p.speed;
        const sb=(l,v,k)=>`<div class="flex items-center gap-2 mb-1.5"><span class="w-8 text-[10px] text-gray-500">${l}</span><span class="w-7 text-xs text-right mono text-gray-300">${v}</span><div class="flex-1 stat-track"><div class="stat-fill" style="width:${v/255*100}%;background:${SC[k]}"></div></div></div>`;
        const evoH=evos.length>1?evos.map((e,i)=>{const hl=e.id===id?'ring-2 ring-cyan-400':'';const ar=i>0?`<span class="text-gray-600 text-xs mx-1">${e.condition||'→'}</span>`:'';return`${ar}<div class="text-center ${hl} rounded-xl p-2"><img src="${spr(e.name)}" data-id="${e.id}" class="w-12 h-12 mx-auto sprite-hover"><p class="text-[10px] mt-1">${e.name_fr||e.name}</p></div>`;}).join(''):'';
        const locH=(Array.isArray(locs)?locs:[]).slice(0,8).map(l=>`<div class="spawn-row"><span class="flex-1 text-sm">${l.route_name}</span><span class="text-xs text-gray-500">${l.region}</span><span class="text-xs mono w-10 text-right" style="color:#69f0ae">${l.rate.toFixed(0)}%</span><span class="text-xs text-gray-500 w-20 text-right">Lv.${l.level_min}-${l.level_max}</span></div>`).join('');
        document.getElementById('dex-grid').classList.add('hidden');
        const d=document.getElementById('dex-detail');d.classList.remove('hidden');
        d.innerHTML=`<button onclick="closeDex()" class="text-sm mb-4 font-medium" style="color:#00e5ff">← Retour au Pokedex</button>
        <div class="glass-card p-8" style="border-top:4px solid ${TC[p.type1]||'#00e5ff'}">
            <div class="flex flex-col md:flex-row gap-8">
                <div class="text-center flex-shrink-0">
                    <img src="${spr(p.name)}" data-id="${p.id}" class="w-36 h-36 mx-auto sprite-hover">
                    <h2 class="text-2xl font-black text-white mt-3">#${String(p.id).padStart(3,'0')} ${p.name_fr||p.name}</h2>
                    ${p.name_fr&&p.name_fr!==p.name?`<p class="text-xs text-gray-500 -mt-1">${p.name}</p>`:''}
                    <div class="flex gap-2 justify-center mt-2">${pill(p.type1)}${p.type2?' '+pill(p.type2):''}</div>
                    <div class="flex flex-wrap gap-1 mt-2 justify-center">${p.ability1?`<button onclick="event.stopPropagation();showAbility(${JSON.stringify(p.ability1)})" class="text-[10px] px-2 py-0.5 rounded cursor-pointer hover:bg-dark-500" style="background:rgba(0,229,255,0.08);color:#00e5ff" title="Voir les Pokemon avec cette capacite">${afr(p.ability1)}</button>`:''} ${p.ability2?`<button onclick="event.stopPropagation();showAbility(${JSON.stringify(p.ability2)})" class="text-[10px] px-2 py-0.5 rounded cursor-pointer hover:bg-dark-500" style="background:rgba(0,229,255,0.08);color:#00e5ff">${afr(p.ability2)}</button>`:''} ${p.hidden_ability?`<button onclick="event.stopPropagation();showAbility(${JSON.stringify(p.hidden_ability)})" class="text-[10px] px-2 py-0.5 rounded cursor-pointer hover:bg-dark-500" style="background:rgba(213,0,249,0.1);color:#d500f9" title="Capacite Cachee">${afr(p.hidden_ability)} (CC)</button>`:''}</div>
                    <div class="flex gap-2 mt-2">
                        <button onclick="event.stopPropagation();toggleFav(${p.id})" class="btn btn-xs ${isFav(p.id)?'btn-warning':'btn-ghost'}">${isFav(p.id)?'★ Favori':'☆ Favoris'}</button>
                        <button onclick="event.stopPropagation();addCompare(${p.id},'${p.name}',[${p.hp},${p.attack},${p.defense},${p.sp_attack},${p.sp_defense},${p.speed}])" class="btn btn-xs btn-info btn-outline">Comparer</button>
                        <button onclick="event.stopPropagation();goIVCalc(${p.id},'${(p.name_fr||p.name).replace(/'/g,"\\'")}')" class="btn btn-xs btn-outline" style="border-color:#76ff03;color:#76ff03">Calculer IVs</button>
                    </div>
                </div>
                <div class="flex-1">
                    <p class="text-xs font-bold tracking-widest text-gray-500 mb-3">STATS DE BASE <span class="text-gray-600">(BST: ${bst})</span></p>
                    <div class="flex gap-6 items-start">
                        <div>${radarSVG([p.hp,p.attack,p.defense,p.sp_attack,p.sp_defense,p.speed])}</div>
                        <div class="flex-1">${sb('HP',p.hp,'hp')}${sb('ATK',p.attack,'attack')}${sb('DEF',p.defense,'defense')}${sb('SPA',p.sp_attack,'sp_attack')}${sb('SPD',p.sp_defense,'sp_defense')}${sb('SPE',p.speed,'speed')}</div>
                    </div>
                    ${(()=>{
                        const nr=recommendNatures(p);
                        let nh='<div class="mt-3 p-3 rounded-lg" style="background:rgba(0,229,255,0.05);border:1px solid rgba(0,229,255,0.08)">';
                        nh+='<p class="text-[10px] font-bold tracking-widest text-gray-500 mb-2">NATURES RECOMMANDEES</p>';
                        if(nr.all.length){
                            nh+='<div class="flex flex-wrap gap-2">';
                            nr.all.forEach((n,i)=>{
                                const star=i===0?'★ ':'';
                                nh+=`<div class="px-3 py-1.5 rounded-lg text-xs ${i===0?'font-bold':'text-gray-400'}" style="background:${i===0?'rgba(0,229,255,0.12)':'rgba(255,255,255,0.03)'};${i===0?'color:#00e5ff':''}">`;
                                nh+=`${star}${n.name} <span class="text-gray-600">(${n.name_en})</span>`;
                                nh+=`<span class="ml-1" style="color:${STAT_COLORS[n.up]}">↑${STAT_NAMES[n.up]}</span>`;
                                nh+=`<span class="ml-1 text-gray-600">↓${STAT_NAMES[n.down]}</span>`;
                                nh+=`</div>`;
                            });
                            nh+='</div>';
                        }
                        nh+='</div>';
                        return nh;
                    })()}
                </div>
            </div>
            ${evoH?`<div class="mt-6 pt-6 border-t border-gray-800"><p class="text-xs font-bold tracking-widest text-gray-500 mb-3">CHAINE D'EVOLUTION</p><div class="flex items-center gap-1 flex-wrap">${evoH}</div></div>`:''}
            ${locH?`<div class="mt-6 pt-6 border-t border-gray-800"><p class="text-xs font-bold tracking-widest text-gray-500 mb-3" style="color:#69f0ae">LOCALISATIONS POKEMMO</p>${locH}</div>`:''}
            <div id="det-moves" class="mt-6 pt-6 border-t border-gray-800"></div>
        </div>`;
        // Load full moveset
        fetch(`/api/pokemon/${id}/moves`).then(r=>r.json()).then(mv=>{
            const el=document.getElementById('det-moves');
            if(!el||!Array.isArray(mv)||!mv.length)return;
            const catIcon={physical:'⚔️',special:'✨',status:'🛡️'};
            // Group by method
            const byMethod={};
            mv.forEach(m=>{const k=m.method;if(!byMethod[k])byMethod[k]=[];byMethod[k].push(m);});
            const methodLabels={'level-up':'PAR NIVEAU','machine':'CT/CS','egg':'EGG MOVES','tutor':'TUTEUR'};
            const methodColors={'level-up':'#40c4ff','machine':'#ffd740','egg':'#69f0ae','tutor':'#d500f9'};
            // Tab buttons
            const methods=Object.keys(byMethod);
            let h=`<div class="flex items-center gap-2 mb-3 flex-wrap">
                <p class="text-xs font-bold tracking-widest text-gray-500" style="color:#ff6e40">MOVESET</p>
                <span class="text-[10px] text-gray-600">${mv.length} moves</span>
                <div class="flex gap-1 ml-auto">`;
            methods.forEach((m,i)=>{
                h+=`<button onclick="filterMoves('${m}')" class="text-[10px] px-2 py-1 rounded font-bold" style="background:${methodColors[m]||'#888'}20;color:${methodColors[m]||'#888'}">${methodLabels[m]||m} (${byMethod[m].length})</button>`;
            });
            h+=`<button onclick="filterMoves('')" class="text-[10px] px-2 py-1 rounded bg-dark-600 text-gray-400">Tous</button></div></div>`;
            h+=`<div id="moves-list" class="max-h-64 overflow-y-auto space-y-0.5">`;
            mv.forEach(m=>{
                const pwrTxt=m.power?m.power:'—';
                const accTxt=m.accuracy?m.accuracy+'%':'—';
                const moveName=m.name_fr||m.name.replace(/-/g,' ').replace(/\b\w/g,c=>c.toUpperCase());
                const catFR={physical:'Phy',special:'Spe',status:'Sta'}[m.category]||m.category.slice(0,3);
                h+=`<div class="flex items-center gap-2 p-1.5 rounded hover:bg-dark-600/30 text-xs move-row" data-method="${m.method}">
                    ${m.method==='level-up'?`<span class="w-8 text-right mono text-gray-500">Lv.${m.level}</span>`:`<span class="w-8 text-right text-gray-600">${catIcon[m.category]||''}</span>`}
                    ${pill(m.type)}
                    <span class="font-bold text-white flex-1">${moveName}</span>
                    <span class="w-8 text-right mono ${m.category==='physical'?'text-orange-400':m.category==='special'?'text-blue-400':'text-gray-500'}">${pwrTxt}</span>
                    <span class="w-10 text-right mono text-gray-500">${accTxt}</span>
                    <span class="w-6 text-right mono text-gray-600">${m.pp}</span>
                    <span class="text-[9px] w-12 text-center text-gray-600">${catFR}</span>
                </div>`;
            });
            h+=`</div>`;
            el.innerHTML=h;
        }).catch(e=>console.error(e));
    }catch(e){console.error(e);}
}
function closeDex(){document.getElementById('dex-detail').classList.add('hidden');document.getElementById('dex-grid').classList.remove('hidden');}

// Combat search with full weakness/resistance breakdown
document.getElementById('battle-input')?.addEventListener('input',async e=>{
    const q=e.target.value.trim();if(q.length<3){document.getElementById('battle-result').classList.add('hidden');return;}
    try{const res=await fetch(`/api/pokemon/search/${q}`).then(r=>r.json());
    if(!Array.isArray(res)||!res.length)return;const p=res[0];const bst=p.hp+p.attack+p.defense+p.sp_attack+p.sp_defense+p.speed;
    // Calculate weaknesses from type chart
    const chartData=await fetch('/api/type-chart').then(r=>r.json());
    const ts=chartData.types,ch=chartData.chart;
    const defTypes=[p.type1];if(p.type2)defTypes.push(p.type2);
    const weak4x=[],weak2x=[],resist025=[],resist05=[],immune=[];
    ts.forEach(atk=>{
        let m=1;defTypes.forEach(dt=>{m*=(ch[atk+'_'+dt]||1);});
        if(m>=4)weak4x.push(atk);else if(m>=2)weak2x.push(atk);
        else if(m===0)immune.push(atk);else if(m<=0.25)resist025.push(atk);
        else if(m<=0.5)resist05.push(atk);
    });
    document.getElementById('battle-result').classList.remove('hidden');
    const btc=TC[p.type1]||'#00e5ff';
    let h=`<div class="glass-card p-5" style="border-left:4px solid ${btc};background:linear-gradient(135deg, ${btc}12 0%, transparent 40%)">
        <div class="flex items-center gap-6 mb-4">
            <img src="${spr(p.name)}" data-id="${p.id}" class="w-20 h-20 sprite-hover">
            <div class="flex-1">
                <h4 class="text-xl font-black text-white">#${String(p.id).padStart(3,'0')} ${p.name_fr||p.name}</h4>
                <div class="flex gap-2 mt-1">${pill(p.type1)}${p.type2?' '+pill(p.type2):''}</div>
                <p class="text-xs text-gray-400 mt-1 mono">BST ${bst} | ${p.attack>=p.sp_attack?'Physique (Atk:'+p.attack+')':'Special (SpA:'+p.sp_attack+')'} | Spe:${p.speed}</p>
            </div>
        </div>`;
    if(weak4x.length) h+=`<div class="mb-2"><span class="text-xs font-bold" style="color:#ff5252">TRES FAIBLE x4 :</span> <span class="ml-1">${weak4x.map(t=>pill(t)).join(' ')}</span></div>`;
    if(weak2x.length) h+=`<div class="mb-2"><span class="text-xs font-bold" style="color:#ff8a80">FAIBLE x2 :</span> <span class="ml-1">${weak2x.map(t=>pill(t)).join(' ')}</span></div>`;
    if(resist05.length) h+=`<div class="mb-2"><span class="text-xs font-bold" style="color:#69f0ae">RESISTE x0.5 :</span> <span class="ml-1">${resist05.map(t=>pill(t)).join(' ')}</span></div>`;
    if(resist025.length) h+=`<div class="mb-2"><span class="text-xs font-bold" style="color:#00e5ff">RESISTE x0.25 :</span> <span class="ml-1">${resist025.map(t=>pill(t)).join(' ')}</span></div>`;
    if(immune.length) h+=`<div class="mb-2"><span class="text-xs font-bold" style="color:#40c4ff">IMMUNITE x0 :</span> <span class="ml-1">${immune.map(t=>pill(t)).join(' ')}</span></div>`;
    h+=`<div class="mt-3 pt-3 border-t border-gray-800 text-xs text-gray-500">
        <span class="font-bold text-white">Attaque avec :</span> ${weak4x.concat(weak2x).map(t=>`<span style="color:${TC[t]}">${tfr(t)}</span>`).join(', ')||'aucune faiblesse'}
        <span class="mx-2">|</span>
        <span class="font-bold text-white">Evite :</span> ${immune.concat(resist025).concat(resist05).map(t=>`<span style="color:${TC[t]}">${tfr(t)}</span>`).join(', ')||'rien a eviter'}
    </div></div>`;
    document.getElementById('battle-result').innerHTML=h;
    }catch(e){console.error(e);}
});

// Damage calc autocomplete
function dmgSearch(input,resultsId){
    const q=input.value.trim();
    const el=document.getElementById(resultsId);
    if(q.length<2){el.classList.add('hidden');return;}
    fetch(`/api/pokemon/search/${encodeURIComponent(q)}`).then(r=>r.json()).then(res=>{
        if(!Array.isArray(res)||!res.length){el.classList.add('hidden');return;}
        el.classList.remove('hidden');
        el.innerHTML=res.slice(0,5).map(p=>`<div class="flex items-center gap-2 p-1 rounded cursor-pointer hover:bg-dark-600" onclick="input=document.getElementById('${input.id}');input.value='${(p.name_fr||p.name).replace(/'/g,"\\'")}';document.getElementById('${resultsId}').classList.add('hidden');dmgCheckStab()"><img src="${spr(p.name)}" class="w-5 h-5"><span class="text-white">${p.name_fr||p.name}</span></div>`).join('');
    }).catch(()=>{});
}
// Type pills for damage calc
function initDmgTypePills(){
    const el=document.getElementById('dmg-type-pills');
    if(!el)return;
    el.innerHTML=Object.entries(TC).map(([t,c])=>`<span class="type-pill cursor-pointer hover:brightness-125" style="background:${c};font-size:8px;padding:2px 6px;opacity:${t==='Normal'?'1':'0.4'}" onclick="selectDmgType('${t}')" id="dmg-tp-${t}">${tfr(t).slice(0,3)}</span>`).join('');
}
function selectDmgType(t){
    document.getElementById('dmg-type').value=t;
    document.querySelectorAll('[id^="dmg-tp-"]').forEach(el=>el.style.opacity='0.4');
    const sel=document.getElementById('dmg-tp-'+t);
    if(sel)sel.style.opacity='1';
    dmgCheckStab();
}
function dmgCheckStab(){
    // Visual STAB indicator (approximate — checks if attacker name matches type)
    const stab=document.getElementById('dmg-stab');
    if(stab)stab.classList.add('hidden'); // simplified — full check needs API
}
initDmgTypePills();

async function calcDmg(){
    const a=document.getElementById('dmg-atk').value,d=document.getElementById('dmg-def').value,pw=document.getElementById('dmg-power').value,tp=document.getElementById('dmg-type').value;
    if(!a||!d)return;
    try{const r=await fetch(`/api/damage?attacker=${a}&defender=${d}&power=${pw}&move_type=${tp}`).then(r=>r.json());
    const el=document.getElementById('dmg-result');el.classList.remove('hidden');
    if(r.error){el.innerHTML=`<span style="color:#ff5252">${r.error}</span>`;return;}
    const ohko=r.max_pct>=100;const pctColor=r.max_pct>=100?'#76ff03':r.max_pct>=50?'#ffd740':'#ff5252';
    const stabBadge=r.stab?'<span class="text-[10px] font-bold px-2 py-0.5 rounded" style="background:rgba(118,255,3,0.15);color:#76ff03">STAB</span>':'';
    el.innerHTML=`<div class="flex items-center gap-4 mb-2">
        <p class="font-bold text-white text-lg">${r.attacker} <span class="text-gray-500">vs</span> ${r.defender}</p>
        ${ohko?'<span class="text-xs font-bold px-2 py-0.5 rounded" style="background:rgba(118,255,3,0.15);color:#76ff03">OHKO</span>':''}
        ${stabBadge}
    </div>
    <div class="flex items-center gap-4">
        <p class="text-2xl mono font-black" style="color:${pctColor}">${r.min_damage}-${r.max_damage}</p>
        <div class="flex-1"><div class="stat-track"><div class="stat-fill" style="width:${Math.min(r.max_pct,100)}%;background:${pctColor}"></div></div></div>
        <p class="text-sm mono" style="color:${pctColor}">${r.min_pct}%-${r.max_pct}%</p>
    </div>
    <p class="text-xs text-gray-500 mt-2">${r.text.replace(/\n/g,'<br>')}</p>`;
    }catch(e){console.error(e);}
}

async function loadChart(){
    try{const d=await fetch('/api/type-chart').then(r=>r.json());const ts=d.types,ch=d.chart;
    window._typeChart=ch;
    let h='<table style="border-collapse:separate;border-spacing:2px"><tr><td class="p-1" style="min-width:60px"></td>';
    ts.forEach(t=>h+=`<td class="p-1 text-center" style="min-width:32px"><div class="type-pill" style="background:${TC[t]};font-size:8px;padding:2px 4px;display:block">${tfr(t).slice(0,3)}</div></td>`);
    h+='</tr>';
    ts.forEach(a=>{
        h+=`<tr><td class="p-1"><div class="type-pill" style="background:${TC[a]};font-size:9px;padding:3px 8px">${tfr(a)}</div></td>`;
        ts.forEach(d2=>{
            const m=ch[a+'_'+d2]||1;
            let bg,tx,clr;
            if(m>=2){bg='rgba(198,40,40,0.7)';tx=m>=4?'4x':'2x';clr='#ff8a80';}
            else if(m===0){bg='rgba(26,35,126,0.7)';tx='0';clr='#82b1ff';}
            else if(m<=0.5){bg='rgba(27,94,32,0.6)';tx=m<=0.25?'1/4':'1/2';clr='#a5d6a7';}
            else{bg='transparent';tx='';clr='transparent';}
            h+=`<td class="text-center font-bold" style="background:${bg};border-radius:4px;padding:4px 2px;font-size:11px;color:${clr};min-width:32px">${tx}</td>`;
        });
        h+='</tr>';
    });
    h+='</table>';
    document.getElementById('type-chart').innerHTML=h;
    const sel=document.getElementById('dmg-type');if(sel){sel.innerHTML='';ts.forEach(t=>sel.innerHTML+=`<option value="${t}">${tfr(t)}</option>`);}
    }catch(e){console.error(e);}
}

// Equipe
let tm=[];
document.getElementById('team-input')?.addEventListener('keydown',async e=>{
    if(e.key!=='Enter')return;const q=e.target.value.trim();if(!q||tm.length>=6)return;
    try{const r=await fetch(`/api/pokemon/search/${q}`).then(r=>r.json());
    if(Array.isArray(r)&&r.length){tm.push(r[0]);e.target.value='';rTm();}
    }catch(e){console.error(e);}
});
function rTm(){
    const s=document.getElementById('team-slots');s.innerHTML='';
    for(let i=0;i<6;i++){
        if(i<tm.length){
            const p=tm[i];
            const bst=p.hp+p.attack+p.defense+p.sp_attack+p.sp_defense+p.speed;
            const topStat=p.attack>=p.sp_attack?`Atk:${p.attack}`:`SpA:${p.sp_attack}`;
            s.innerHTML+=`<div class="dex-card p-3 relative" onclick="rmTm(${i})" style="border-top:3px solid ${TC[p.type1]||'#888'};background:linear-gradient(135deg, ${TC[p.type1]||'#888'}15 0%, rgba(13,17,23,0.6) 60%)" title="Clic pour retirer">
                <button class="absolute top-1 right-1 text-gray-700 hover:text-red-400 text-xs">✕</button>
                <img src="${spr(p.name)}" data-id="${p.id}" class="w-16 h-16 mx-auto sprite-hover">
                <p class="text-xs font-bold text-white mt-1">${p.name_fr||p.name}</p>
                <div class="flex gap-1 justify-center mt-1">${pill(p.type1)}${p.type2?' '+pill(p.type2):''}</div>
                <p class="text-[9px] text-gray-500 mt-1 mono">${topStat} | Spe:${p.speed} | BST:${bst}</p>
            </div>`;
        }else{
            s.innerHTML+=`<div class="glass-card border-2 border-dashed border-gray-800 p-3 text-center h-36 flex items-center justify-center"><span class="text-gray-700 text-sm">Slot ${i+1}</span></div>`;
        }
    }
    aTm();
}
function rmTm(i){tm.splice(i,1);rTm();}
function clearTm(){tm=[];rTm();}
function toggleSD(){document.getElementById('sd-import').classList.toggle('hidden');}
async function importSD(){
    const t=document.getElementById('sd-text').value;if(!t.trim())return;
    try{const r=await fetch('/api/import-showdown',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t})}).then(r=>r.json());
    tm=r.filter(p=>p.id);document.getElementById('sd-import').classList.add('hidden');document.getElementById('sd-text').value='';rTm();
    }catch(e){console.error(e);}
}
async function aTm(){
    const el=document.getElementById('team-cov');if(!tm.length){el.innerHTML='<span class="text-gray-600">Ajoute des Pokemon...</span>';return;}
    try{const d=await fetch('/api/type-chart').then(r=>r.json());const ts=d.types,ch=d.chart;
    const cov=new Set();tm.forEach(p=>{[p.type1,p.type2].filter(Boolean).forEach(a=>{ts.forEach(df=>{if((ch[a+'_'+df]||1)>1)cov.add(df);});});});
    const unc=ts.filter(t=>!cov.has(t));
    const wk={};ts.forEach(t=>wk[t]=0);tm.forEach(p=>{ts.forEach(a=>{let m=ch[a+'_'+p.type1]||1;if(p.type2)m*=(ch[a+'_'+p.type2]||1);if(m>1)wk[a]++;});});
    const dng=Object.entries(wk).filter(([,c])=>c>=3).sort((a,b)=>b[1]-a[1]);
    let h=`<p><span style="color:#00e5ff" class="font-bold">Couverture :</span> ${Math.round(cov.size/ts.length*100)}% (${cov.size}/${ts.length})</p>`;
    if(unc.length)h+=`<p class="text-sm text-gray-500 mt-1">Non couverts : ${unc.map(t=>pill(t)).join(' ')}</p>`;
    if(dng.length)h+=`<p class="mt-2 font-bold" style="color:#ff5252">DANGER : ${dng.map(([t,c])=>`${pill(t)} (${c}/${tm.length})`).join(' ')}</p>`;
    else h+=`<p class="mt-2 font-bold" style="color:#69f0ae">Bon equilibre !</p>`;
    el.innerHTML=h;
    // Defensive matrix
    const matEl=document.getElementById('team-matrix');
    const matCard=document.getElementById('team-matrix-card');
    if(matEl&&tm.length>=2){
        matCard.style.display='block';
        let mh='<table><tr><td class="p-1"></td>';
        ts.forEach(t=>mh+=`<td class="p-1 text-center"><span class="type-pill" style="background:${TC[t]};font-size:7px;padding:1px 3px">${tfr(t).slice(0,3)}</span></td>`);
        mh+='</tr>';
        tm.forEach(p=>{
            mh+=`<tr><td class="p-1 font-bold text-white text-[10px] whitespace-nowrap">${(p.name_fr||p.name).slice(0,10)}</td>`;
            ts.forEach(atk=>{
                let m=ch[atk+'_'+p.type1]||1;if(p.type2)m*=(ch[atk+'_'+p.type2]||1);
                const bg=m>=2?'rgba(255,82,82,0.4)':m===0?'rgba(64,196,255,0.3)':m<1?'rgba(105,240,174,0.2)':'';
                const tx=m>=4?'4x':m>=2?'2x':m===0?'0':m<=0.25?'1/4':m<=0.5?'1/2':'';
                const cl=m>=2?'color:#ff8a80':m===0?'color:#82b1ff':m<1?'color:#a5d6a7':'color:transparent';
                mh+=`<td class="p-1 text-center text-[10px] font-bold" style="background:${bg};border-radius:3px;${cl}">${tx}</td>`;
            });
            mh+='</tr>';
        });
        matEl.innerHTML=mh;
    }else if(matCard){matCard.style.display='none';}
    }catch(e){console.error(e);}
}

// Collection
function showToast(msg){
    const t=document.createElement('div');
    t.textContent=msg;
    t.style.cssText='position:fixed;bottom:24px;right:24px;background:rgba(0,229,255,0.15);color:#00e5ff;border:1px solid rgba(0,229,255,0.3);padding:12px 24px;border-radius:12px;font-size:14px;font-weight:600;z-index:9999;animation:fadeIn 0.3s ease';
    document.body.appendChild(t);
    setTimeout(()=>t.remove(),3000);
}

// Make collection interactive
let _colPage=0;const _COL_PAGE=100;let _colPk=[];
async function loadCol(){
    window._cl=true;
    try{const pk=await fetch('/api/pokemon/all').then(r=>r.json());if(!Array.isArray(pk))return;
    _colPk=pk;_colPage=0;
    const g=document.getElementById('col-grid');g.innerHTML='';
    _appendCol();
    const caught=JSON.parse(localStorage.getItem('caught')||'[]');
    updateColCount(caught.length);
    updateRegionProgress(caught);
    }catch(e){console.error(e);}
}
function updateRegionProgress(caught){
    const regions=[
        {name:'Kanto',start:1,end:151,color:'#40c4ff'},
        {name:'Johto',start:152,end:251,color:'#ffd740'},
        {name:'Hoenn',start:252,end:386,color:'#69f0ae'},
        {name:'Sinnoh',start:387,end:493,color:'#d500f9'},
        {name:'Unova',start:494,end:649,color:'#ff6e40'},
    ];
    const el=document.getElementById('col-region-progress');
    if(!el)return;
    el.innerHTML=regions.map(r=>{
        const total=r.end-r.start+1;
        const have=caught.filter(id=>id>=r.start&&id<=r.end).length;
        const pct=Math.round(have/total*100);
        return`<div class="p-2 rounded-lg text-center" style="background:${r.color}08;border:1px solid ${r.color}20">
            <p class="text-[10px] font-bold" style="color:${r.color}">${r.name}</p>
            <p class="text-sm font-black text-white mono">${have}/${total}</p>
            <div class="stat-track mt-1 h-1.5 rounded"><div class="stat-fill rounded" style="width:${pct}%;background:${r.color}"></div></div>
        </div>`;
    }).join('');
}
function filterCol(range){
    if(!_colPk.length)return;
    const caught=JSON.parse(localStorage.getItem('caught')||'[]');
    let filtered=_colPk;
    if(range==='missing'){
        filtered=_colPk.filter(p=>!caught.includes(p.id));
    }else if(range){
        const[s,e]=range.split('-').map(Number);
        filtered=_colPk.filter(p=>p.id>=s&&p.id<=e);
    }
    _colPk=filtered;_colPage=0;
    document.getElementById('col-grid').innerHTML='';
    _appendCol();
    // Reload full list for next filter (without re-fetching)
    if(range)fetch('/api/pokemon/all').then(r=>r.json()).then(pk=>{if(Array.isArray(pk))_colPk=pk;});
}
function exportColText(){
    const caught=JSON.parse(localStorage.getItem('caught')||'[]');
    if(!caught.length){showToast('Collection vide');return;}
    const names=_colPk.filter(p=>caught.includes(p.id)).map(p=>p.name_fr||p.name);
    navigator.clipboard.writeText(`Ma collection PokeMMO (${names.length}/649):\n${names.join(', ')}`);
    showToast(`${names.length} Pokemon copies dans le presse-papier !`);
}
function _appendCol(){
    const g=document.getElementById('col-grid');
    const caught=JSON.parse(localStorage.getItem('caught')||'[]');
    const start=_colPage*_COL_PAGE;const batch=_colPk.slice(start,start+_COL_PAGE);
    if(!batch.length)return;
    const frag=document.createDocumentFragment();
    batch.forEach(p=>{
        const isCaught=caught.includes(p.id);
        const d=document.createElement('div');d.className='dex-card p-1 '+(isCaught?'':'opacity-30')+' hover:opacity-100 transition cursor-pointer';
        d.style.borderBottom='2px solid '+(TC[p.type1]||'#888');if(isCaught)d.style.boxShadow='0 0 8px rgba(105,240,174,0.3)';
        d.id='col-'+p.id;d.title=(p.name_fr||p.name)+' — clic=capturer, double-clic=fiche';
        d.onclick=()=>toggleCatch(p.id);d.ondblclick=()=>{go('pokedex');setTimeout(()=>showP(p.id),300);};
        d.innerHTML=`<img src="${spr(p.name)}" data-id="${p.id}" class="w-8 h-8 mx-auto" loading="lazy"><p class="text-[7px] text-gray-600">${p.id}</p>`;
        frag.appendChild(d);
    });
    g.appendChild(frag);_colPage++;
    let btn=document.getElementById('col-load-more');
    if(start+_COL_PAGE<_colPk.length){
        if(!btn){btn=document.createElement('button');btn.id='col-load-more';btn.className='btn btn-ghost btn-sm text-neon-cyan w-full mt-4';btn.onclick=()=>_appendCol();g.parentNode.appendChild(btn);}
        btn.textContent=`Charger plus (${_colPk.length-start-_COL_PAGE} restants)`;btn.classList.remove('hidden');
    }else if(btn){btn.classList.add('hidden');}
}
function toggleCatch(id){
    let caught=JSON.parse(localStorage.getItem('caught')||'[]');
    if(caught.includes(id)){caught=caught.filter(x=>x!==id);}else{caught.push(id);}
    localStorage.setItem('caught',JSON.stringify(caught));
    const el=document.getElementById('col-'+id);
    if(el){
        if(caught.includes(id)){el.classList.remove('opacity-30');el.style.boxShadow='0 0 8px rgba(105,240,174,0.3)';}
        else{el.classList.add('opacity-30');el.style.boxShadow='';}
    }
    updateColCount(caught.length);
    updateRegionProgress(caught);
}
function updateColCount(n){
    const hdr=document.getElementById('col-header-count');
    if(hdr) hdr.textContent=n+' / 649';
    const bar=document.getElementById('col-progress-bar');
    if(bar) bar.style.width=(n/649*100)+'%';
    // Also update dashboard collection card
    const dc=document.getElementById('col-count');
    if(dc) dc.textContent=n;
    const db=document.getElementById('col-bar');
    if(db) db.style.width=(n/649*100)+'%';
    const dp=document.getElementById('col-pct');
    if(dp) dp.textContent=Math.round(n/649*100)+'%';
}

// Guide
async function loadGuide(region){
    try{const steps=await fetch(`/api/progression/${region}`).then(r=>r.json());
    const el=document.getElementById('guide-content');
    if(!Array.isArray(steps)||!steps.length){el.innerHTML='<p class="text-gray-500">Aucune donnee pour cette region.</p>';return;}
    const done=JSON.parse(localStorage.getItem('guide_'+region)||'[]');
    const total=steps.length;const completed=done.length;
    el.innerHTML=`<div class="mb-4"><div class="flex justify-between text-sm mb-1"><span class="text-gray-400">Progression ${region}</span><span style="color:#69f0ae" class="font-bold">${completed}/${total}</span></div><div class="stat-track h-2 rounded"><div class="stat-fill bg-neon-green rounded" style="width:${total?completed/total*100:0}%"></div></div></div>`+
    steps.map((s,i)=>{
        const checked=done.includes(s.step);
        return `<div class="glass-card p-4 mb-3 flex items-start gap-4 ${checked?'opacity-60':''}">
            <input type="checkbox" ${checked?'checked':''} onchange="toggleGuideStep('${region}',${s.step})" class="mt-1 w-5 h-5 rounded accent-cyan-400 cursor-pointer flex-shrink-0">
            <div class="flex-1">
                <p class="font-bold text-white ${checked?'line-through':''}">${s.step}. ${s.title}</p>
                <p class="text-sm text-gray-400 mt-1">${s.description||''}</p>
                <div class="flex flex-wrap gap-3 mt-2 text-xs">
                    ${s.location?`<span class="text-gray-500">📍 ${s.location}</span>`:''}
                    ${s.recommended_level?`<span style="color:#69f0ae">Niv. ${s.recommended_level}+</span>`:''}
                    ${s.badge_number!=null&&s.badge_number>0?`<span style="color:#ffd740">🏅 Badge ${s.badge_number}</span>`:''}
                </div>
                ${s.key_items?`<div class="mt-2 p-2 rounded" style="background:rgba(255,215,64,0.06);border:1px solid rgba(255,215,64,0.15)"><p class="text-[10px] font-bold tracking-wider mb-1" style="color:#ffd740">OBJETS CLES</p><p class="text-xs text-gray-300">${s.key_items}</p></div>`:''}
                ${s.tms?`<div class="mt-2 p-2 rounded" style="background:rgba(213,0,249,0.06);border:1px solid rgba(213,0,249,0.15)"><p class="text-[10px] font-bold tracking-wider mb-1" style="color:#d500f9">CT / CS</p><p class="text-xs text-gray-300">${s.tms}</p></div>`:''}
                ${s.tips?`<div class="mt-2 p-2 rounded" style="background:rgba(0,229,255,0.06);border:1px solid rgba(0,229,255,0.15)"><p class="text-[10px] font-bold tracking-wider mb-1" style="color:#00e5ff">CONSEIL</p><p class="text-xs text-gray-300">${s.tips}</p></div>`:''}
            </div>
        </div>`;
    }).join('');
    }catch(e){console.error(e);}
}
function toggleGuideStep(region,step){
    let done=JSON.parse(localStorage.getItem('guide_'+region)||'[]');
    if(done.includes(step)){done=done.filter(s=>s!==step);}else{done.push(step);}
    localStorage.setItem('guide_'+region,JSON.stringify(done));
    loadGuide(region);
}

// Game status check
async function checkGame(){
    try{const r=await fetch('/api/game-status').then(r=>r.json());
    const el=document.getElementById('game-status-dot');
    const txt=document.getElementById('game-status-text');
    if(el&&txt){
        if(r.connected){el.className='w-2 h-2 rounded-full bg-neon-green';txt.textContent='PokeMMO detecte';}
        else{el.className='w-2 h-2 rounded-full bg-red-500';txt.textContent='Hors ligne';}
    }}catch(e){}
}
setInterval(checkGame,5000);

// Shiny counter
let shData=JSON.parse(localStorage.getItem('shiny_data')||'{"session":0,"total":0,"shinies":0,"start":0,"history":[],"lastShinyAt":0}');
if(!shData.start)shData.start=Date.now();
if(!shData.history)shData.history=[];
if(!shData.lastShinyAt)shData.lastShinyAt=0;

function shinyAdd(n){shData.session+=n;shData.total+=n;shinyUpdate();}
function shinyFound(){
    document.getElementById('shiny-name-input').value='';
    document.getElementById('shiny-modal-preview').classList.add('hidden');
    document.getElementById('shiny-modal').showModal();
    // Auto-complete preview
    document.getElementById('shiny-name-input').oninput=async function(){
        const q=this.value.trim();if(q.length<2)return;
        try{const r=await fetch(`/api/pokemon/search/${q}`).then(r=>r.json());
        if(Array.isArray(r)&&r.length){
            document.getElementById('shiny-modal-sprite').src=spr(r[0].name);
            document.getElementById('shiny-modal-preview').classList.remove('hidden');
        }}catch(e){}
    };
}
function confirmShiny(){
    const name=document.getElementById('shiny-name-input').value||'Inconnu';
    const encounters=shData.session-shData.lastShinyAt;
    shData.history.push({name,encounters,total:shData.total,date:new Date().toISOString().slice(0,10)});
    shData.shinies++;
    shData.lastShinyAt=shData.session;
    shinyUpdate();
    document.getElementById('shiny-modal').close();
    showToast(`SHINY ${name.toUpperCase()} TROUVE apres ${encounters.toLocaleString()} rencontres !`);
    fetch('/api/sound/shiny',{method:'POST'}).catch(()=>{});
}
function shinyReset(){shData.session=0;shData.lastShinyAt=0;shData.start=Date.now();shinyUpdate();showToast('Session reinitialisee');}
function deleteShiny(idx){shData.history.splice(idx,1);shData.shinies=shData.history.length;shinyUpdate();showToast('Shiny supprime');}
function shinyUpdate(){
    localStorage.setItem('shiny_data',JSON.stringify(shData));
    const el=id=>document.getElementById(id);
    if(el('sh-session'))el('sh-session').textContent=shData.session.toLocaleString();
    if(el('sh-total'))el('sh-total').textContent=shData.total.toLocaleString();
    if(el('sh-shinies'))el('sh-shinies').textContent=shData.shinies;
    // Rate from selector
    const rateMod=parseInt(document.getElementById('sh-rate-mod')?.value||'30000');
    const prob=1-Math.pow(1-1/rateMod,shData.session);
    const pct=(prob*100).toFixed(2);
    if(el('sh-prob'))el('sh-prob').textContent=pct+'%';
    if(el('sh-prob2'))el('sh-prob2').textContent=pct+'%';
    if(el('sh-bar')){
        el('sh-bar').style.width=Math.min(prob*100,100)+'%';
        el('sh-bar').style.background=prob>0.5?'#ff5252':prob>0.25?'#ffd740':'#69f0ae';
    }
    // History
    const hist=el('sh-history');
    if(hist&&shData.history.length){
        hist.innerHTML=shData.history.slice().reverse().map((h,i)=>{
            const idx=shData.history.length-1-i;
            return `<div class="flex items-center gap-3 p-2 glass-card"><span style="color:#ffd740" class="font-bold">✨ ${h.name}</span><span class="text-gray-500">apres ${h.encounters.toLocaleString()} rencontres</span><span class="text-gray-600 text-xs ml-auto">${h.date}</span><button onclick="deleteShiny(${idx})" class="btn btn-xs btn-ghost text-gray-600 hover:text-red-400">✕</button></div>`;
        }).join('');
    }
    // Stats
    if(shData.history.length){
        const encs=shData.history.map(h=>h.encounters);
        const avg=Math.round(encs.reduce((a,b)=>a+b,0)/encs.length);
        const best=Math.min(...encs);
        const worst=Math.max(...encs);
        if(el('sh-avg'))el('sh-avg').textContent=avg.toLocaleString();
        if(el('sh-best'))el('sh-best').textContent=best.toLocaleString();
        if(el('sh-worst'))el('sh-worst').textContent=worst.toLocaleString();
        // Chart
        const chartEl=document.getElementById('sh-chart');
        const chartCard=document.getElementById('sh-chart-card');
        if(chartEl&&shData.history.length>=1){
            chartCard.style.display='block';
            const w=chartEl.clientWidth||400,h=120;
            const maxE=Math.max(...encs,1);
            const barW=Math.min(40,w/encs.length-4);
            let svg=`<svg viewBox="0 0 ${w} ${h}" class="w-full h-full">`;
            // Average line
            const avgY=h-avg/maxE*(h-20)-10;
            svg+=`<line x1="0" y1="${avgY}" x2="${w}" y2="${avgY}" stroke="rgba(0,229,255,0.3)" stroke-width="1" stroke-dasharray="4"/>`;
            svg+=`<text x="${w-5}" y="${avgY-4}" text-anchor="end" fill="rgba(0,229,255,0.5)" font-size="9">moy: ${avg.toLocaleString()}</text>`;
            // Bars
            encs.forEach((e,i)=>{
                const x=i*(barW+4)+2;
                const barH=Math.max(4,e/maxE*(h-20));
                const y=h-barH-10;
                const color=e<=avg?'#69f0ae':'#ff5252';
                svg+=`<rect x="${x}" y="${y}" width="${barW}" height="${barH}" rx="3" fill="${color}" opacity="0.7"/>`;
                svg+=`<text x="${x+barW/2}" y="${h-2}" text-anchor="middle" fill="#888" font-size="8">${shData.history[i].name.slice(0,4)}</text>`;
                svg+=`<text x="${x+barW/2}" y="${y-3}" text-anchor="middle" fill="${color}" font-size="8">${(e/1000).toFixed(1)}k</text>`;
            });
            svg+=`</svg>`;
            chartEl.innerHTML=svg;
        }
    }
    // Encounter rate & time estimates
    if(shData.start&&shData.session>0){
        const elapsed=(Date.now()-shData.start)/3600000; // hours
        if(elapsed>0.01){
            const rate=Math.round(shData.session/elapsed);
            if(el('sh-rate'))el('sh-rate').textContent=rate.toLocaleString()+'/h';
            if(rate>0){
                // Encounters needed for 50% and 90% chance
                const n50=Math.ceil(Math.log(0.5)/Math.log(1-1/rateMod));
                const n90=Math.ceil(Math.log(0.1)/Math.log(1-1/rateMod));
                const remaining50=Math.max(0,n50-shData.session);
                const remaining90=Math.max(0,n90-shData.session);
                const h50=remaining50/rate,h90=remaining90/rate;
                const fmt=h=>h<1?Math.round(h*60)+'min':h<24?h.toFixed(1)+'h':Math.round(h/24)+'j';
                if(el('sh-eta50'))el('sh-eta50').textContent=remaining50<=0?'Depasse !':fmt(h50);
                if(el('sh-eta90'))el('sh-eta90').textContent=remaining90<=0?'Depasse !':fmt(h90);
            }
        }
    }
}
// Timer
setInterval(()=>{
    if(!shData.start)return;
    const d=Math.floor((Date.now()-shData.start)/1000);
    const h=Math.floor(d/3600),m=Math.floor(d%3600/60),s=d%60;
    const el=document.getElementById('sh-time');
    if(el)el.textContent=`${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
},1000);

// Global search — Pokemon, types, routes
async function globalSearch(q){
    const el=document.getElementById('search-results');
    if(q.length<2){el.classList.add('hidden');return;}
    let html='';
    const close=`document.getElementById('search-results').classList.add('hidden');document.getElementById('global-search').value='';`;
    try{
        const ql=q.toLowerCase();
        // Search by type (FR or EN)
        const typeMatch=Object.entries(TFR).find(([en,fr])=>fr.toLowerCase().startsWith(ql)||en.toLowerCase().startsWith(ql));
        if(typeMatch){
            const[typeEN,typeFR]=typeMatch;
            html+=`<p class="text-[9px] font-bold tracking-widest text-gray-600 px-1 pt-1">TYPE</p>`;
            html+=`<div class="flex items-center gap-2 p-1.5 rounded cursor-pointer hover:bg-dark-600" onclick="go('pokedex');setTimeout(()=>fDex('${typeEN}'),300);${close}">${pill(typeEN)} <span class="text-white text-xs">Tous les ${typeFR}</span></div>`;
        }
        // Search Pokemon
        const res=await fetch(`/api/pokemon/search/${encodeURIComponent(q)}`).then(r=>r.json());
        if(Array.isArray(res)&&res.length){
            html+=`<p class="text-[9px] font-bold tracking-widest text-gray-600 px-1 pt-1">POKEMON</p>`;
            html+=res.slice(0,6).map(p=>`<div class="flex items-center gap-2 p-1.5 rounded cursor-pointer hover:bg-dark-600" onclick="go('pokedex');setTimeout(()=>showP(${p.id}),300);${close}"><img src="${spr(p.name)}" class="w-6 h-6"><span class="text-white font-medium">${p.name_fr||p.name}</span><span class="text-gray-600 text-[10px]">#${p.id}</span></div>`).join('');
        }
        // Search routes
        try{
            const routes=await fetch(`/api/routes?search=${encodeURIComponent(q)}`).then(r=>r.json());
            if(Array.isArray(routes)&&routes.length){
                html+=`<p class="text-[9px] font-bold tracking-widest text-gray-600 px-1 pt-2">ROUTES</p>`;
                html+=routes.slice(0,4).map(r=>`<div class="flex items-center gap-2 p-1.5 rounded cursor-pointer hover:bg-dark-600" onclick="go('guide');${close}"><span>📍</span><span class="text-white text-xs">${r.display_name||r.name}</span><span class="text-gray-600 text-[10px]">${r.region}</span></div>`).join('');
            }
        }catch(e){}
        if(html){el.classList.remove('hidden');el.innerHTML=html;}
        else{el.classList.add('hidden');}
    }catch(e){el.classList.add('hidden');}
}

// Radar chart SVG for Pokemon detail
function radarSVG(stats){
    const labels=['HP','Atk','Def','SpA','SpD','Spe'];
    const colors=['#78C850','#F08030','#F8D030','#6890F0','#78C850','#F85888'];
    const cx=100,cy=100,r=80,n=6;
    const angle=(i)=>Math.PI*2*i/n-Math.PI/2;
    // Grid
    let svg=`<svg viewBox="0 0 200 200" class="w-48 h-48">`;
    [0.33,0.66,1].forEach(level=>{
        let pts='';for(let i=0;i<n;i++){const a=angle(i);pts+=`${cx+r*level*Math.cos(a)},${cy+r*level*Math.sin(a)} `;}
        svg+=`<polygon points="${pts}" fill="none" stroke="rgba(0,229,255,0.1)" stroke-width="1"/>`;
    });
    // Axes
    for(let i=0;i<n;i++){const a=angle(i);svg+=`<line x1="${cx}" y1="${cy}" x2="${cx+r*Math.cos(a)}" y2="${cy+r*Math.sin(a)}" stroke="rgba(0,229,255,0.08)" stroke-width="1"/>`;}
    // Stat polygon with animation
    let pts='';for(let i=0;i<n;i++){const a=angle(i);const v=Math.min(stats[i]/255,1);pts+=`${cx+r*v*Math.cos(a)},${cy+r*v*Math.sin(a)} `;}
    // Start from center, animate to full
    let ptsZero='';for(let i=0;i<n;i++) ptsZero+=`${cx},${cy} `;
    svg+=`<polygon fill="rgba(0,229,255,0.15)" stroke="#00e5ff" stroke-width="2"><animate attributeName="points" from="${ptsZero}" to="${pts}" dur="0.6s" fill="freeze" calcMode="spline" keySplines="0.4 0 0.2 1"/></polygon>`;
    // Dots at each stat point
    for(let i=0;i<n;i++){const a=angle(i);const v=Math.min(stats[i]/255,1);
        svg+=`<circle cx="${cx+r*v*Math.cos(a)}" cy="${cy+r*v*Math.sin(a)}" r="3" fill="#00e5ff" opacity="0"><animate attributeName="opacity" from="0" to="1" begin="0.5s" dur="0.3s" fill="freeze"/></circle>`;
    }
    // Labels
    for(let i=0;i<n;i++){const a=angle(i);const lx=cx+(r+18)*Math.cos(a);const ly=cy+(r+18)*Math.sin(a);
        svg+=`<text x="${lx}" y="${ly}" text-anchor="middle" dominant-baseline="middle" fill="${colors[i]}" font-size="10" font-weight="700">${labels[i]}</text>`;
        svg+=`<text x="${lx}" y="${ly+11}" text-anchor="middle" fill="#888" font-size="9">${stats[i]}</text>`;
    }
    svg+=`</svg>`;return svg;
}

// Export collection
function exportCol(){
    const caught=JSON.parse(localStorage.getItem('caught')||'[]');
    const data=JSON.stringify({caught,exported:new Date().toISOString()},null,2);
    const blob=new Blob([data],{type:'application/json'});
    const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='pokemmo-collection.json';a.click();
    showToast('Collection exportee !');
}

// Import collection
function importCol(event){
    const file=event.target.files[0];if(!file)return;
    const reader=new FileReader();
    reader.onload=function(e){
        try{
            const data=JSON.parse(e.target.result);
            if(data.caught&&Array.isArray(data.caught)){
                localStorage.setItem('caught',JSON.stringify(data.caught));
                showToast(`Collection importee : ${data.caught.length} Pokemon !`);
                if(window._cl) loadCol();
                updateColCount(data.caught.length);
            }
        }catch(err){showToast('Erreur: fichier invalide');}
    };
    reader.readAsText(file);
}

// Dynamic Options stats
async function loadOptStats(){
    try{const s=await fetch('/api/stats').then(r=>r.json());
    const el=id=>document.getElementById(id);
    if(el('opt-poke'))el('opt-poke').textContent=s.pokemon;
    if(el('opt-routes'))el('opt-routes').textContent=s.routes;
    if(el('opt-spawns'))el('opt-spawns').textContent=s.spawns;
    if(el('opt-sprites'))el('opt-sprites').textContent=s.sprites;
    }catch(e){}
}

// OCR cache stats (auto-refresh every 5s when on settings page)
setInterval(()=>{if(!document.getElementById('page-settings').classList.contains('hidden'))loadCacheStats();},5000);
async function loadCacheStats(){
    try{
        const data=await fetch('/api/ocr/cache-stats').then(r=>r.json());
        if(data.error){document.getElementById('cache-stats').innerHTML=`<p class="text-red-400 text-sm">${data.error}</p>`;return;}
        const rc=data.route_cache,pc=data.pokemon_cache;
        document.getElementById('cache-route-hits').textContent=rc.hits;
        document.getElementById('cache-route-misses').textContent=rc.misses;
        document.getElementById('cache-route-ratio').textContent=(rc.ratio*100).toFixed(1)+'%';
        document.getElementById('cache-route-size').textContent=rc.size+'/'+rc.maxsize;
        document.getElementById('cache-pokemon-hits').textContent=pc.hits;
        document.getElementById('cache-pokemon-misses').textContent=pc.misses;
        document.getElementById('cache-pokemon-ratio').textContent=(pc.ratio*100).toFixed(1)+'%';
        document.getElementById('cache-pokemon-size').textContent=pc.size+'/'+pc.maxsize;
    }catch(e){console.error(e);}
}

// IV Calculator
let _ivPokemonId=null;
async function ivImportOverlay(){
    try{
        const d=await fetch('/api/ocr/latest').then(r=>r.json());
        if(!d.active||!d.opponent){showToast('Overlay inactif ou pas en combat');return;}
        // Search for the opponent pokemon
        const res=await fetch(`/api/pokemon/search/${encodeURIComponent(d.opponent)}`).then(r=>r.json());
        if(Array.isArray(res)&&res.length){
            const p=res[0];
            ivSelectPokemon(p.id, p.name_fr||p.name);
            if(d.level)document.getElementById('iv-level').value=d.level;
            showToast(`Import: ${p.name_fr||p.name} Niv.${d.level||'?'}`);
        }else{showToast('Pokemon non trouve: '+d.opponent);}
    }catch(e){showToast('Erreur import overlay');}
}
function ivSearchPokemon(q){
    const el=document.getElementById('iv-pokemon-results');
    if(q.length<2){el.classList.add('hidden');return;}
    fetch(`/api/pokemon/search/${q}`).then(r=>r.json()).then(res=>{
        if(!Array.isArray(res)||!res.length){el.classList.add('hidden');return;}
        el.classList.remove('hidden');
        el.innerHTML=res.slice(0,6).map(p=>`<div class="flex items-center gap-2 p-1 rounded cursor-pointer hover:bg-dark-600" onclick="ivSelectPokemon(${p.id},'${(p.name_fr||p.name).replace(/'/g,"\\'")}')"><img src="${spr(p.name)}" class="w-6 h-6"><span class="text-white">${p.name_fr||p.name}</span><span class="text-gray-600 text-[10px]">#${p.id}</span></div>`).join('');
    }).catch(()=>{});
}
function ivSelectPokemon(id,name){
    _ivPokemonId=id;
    document.getElementById('iv-pokemon').value=name;
    document.getElementById('iv-pokemon-id').value=id;
    document.getElementById('iv-pokemon-results').classList.add('hidden');
    // Fetch and show base stats as reference
    fetch(`/api/pokemon/${id}`).then(r=>r.json()).then(p=>{
        const ref=document.getElementById('iv-base-stats');
        if(!ref)return;
        const stats=[p.hp,p.attack,p.defense,p.sp_attack,p.sp_defense,p.speed];
        const labels=['PV','Atq','Def','A.Spe','D.Spe','Vit'];
        const colors=['#78C850','#F08030','#F8D030','#6890F0','#78C850','#F85888'];
        ref.innerHTML=stats.map((v,i)=>`<span class="text-[10px] px-1.5 py-0.5 rounded" style="background:${colors[i]}20;color:${colors[i]}">${labels[i]}:${v}</span>`).join(' ');
        ref.classList.remove('hidden');
    }).catch(()=>{});
}
async function calcIVs(){
    const id=_ivPokemonId||document.getElementById('iv-pokemon-id').value;
    if(!id){showToast('Selectionnez un Pokemon');return;}
    const btn=document.getElementById('iv-calc-btn');
    btn.textContent='Calcul en cours...';btn.disabled=true;
    const level=parseInt(document.getElementById('iv-level').value)||50;
    const nature=document.getElementById('iv-nature').value;
    const stats=[
        parseInt(document.getElementById('iv-hp').value)||0,
        parseInt(document.getElementById('iv-atk').value)||0,
        parseInt(document.getElementById('iv-def').value)||0,
        parseInt(document.getElementById('iv-spa').value)||0,
        parseInt(document.getElementById('iv-spd').value)||0,
        parseInt(document.getElementById('iv-spe').value)||0,
    ];
    const evs=document.getElementById('iv-has-evs').checked?[
        parseInt(document.getElementById('iv-ev-hp').value)||0,
        parseInt(document.getElementById('iv-ev-atk').value)||0,
        parseInt(document.getElementById('iv-ev-def').value)||0,
        parseInt(document.getElementById('iv-ev-spa').value)||0,
        parseInt(document.getElementById('iv-ev-spd').value)||0,
        parseInt(document.getElementById('iv-ev-spe').value)||0,
    ]:[0,0,0,0,0,0];
    try{
        const r=await fetch('/api/iv-calc',{method:'POST',headers:{'Content-Type':'application/json'},
            body:JSON.stringify({pokemon_id:parseInt(id),level,nature,stats,evs})}).then(r=>r.json());
        if(r.error){showToast(r.error);return;}
        const el=document.getElementById('iv-results');el.classList.remove('hidden');
        const colors=['#78C850','#F08030','#F8D030','#6890F0','#78C850','#F85888'];
        const impossible=r.results.filter(s=>s.possible_ivs.length===0);
        let html='';
        if(impossible.length){
            html+=`<div class="p-3 rounded mb-3" style="background:rgba(255,82,82,0.1);border:1px solid rgba(255,82,82,0.3)">
                <p class="text-sm font-bold text-red-400">${impossible.length} stat(s) impossible(s) — verifiez les valeurs entrees</p>
                <p class="text-[10px] text-gray-500 mt-1">Stats incorrectes : ${impossible.map(s=>s.name).join(', ')}. Verifiez le niveau, la nature, et les EVs.</p>
            </div>`;
        }
        html+='<div class="space-y-3">';
        r.results.forEach((s,i)=>{
            const ivText=s.possible_ivs.length===0?'<span class="text-red-400 font-bold">Impossible</span>'
                :s.exact?`<span class="font-black" style="color:${s.min_iv>=26?'#76ff03':s.min_iv>=16?'#ffd740':'#ff5252'}">${s.min_iv}</span>`
                :`<span style="color:${colors[i]}">${s.min_iv} - ${s.max_iv}</span>`;
            const bar=s.max_iv!==null?`<div class="stat-track mt-1"><div class="stat-fill" style="width:${(s.max_iv||0)/31*100}%;background:${colors[i]}"></div></div>`:'';
            html+=`<div class="flex items-center gap-3">
                <span class="w-16 text-xs text-gray-400">${s.name}</span>
                <span class="w-8 text-xs text-right mono text-gray-500">${s.base}</span>
                <span class="w-8 text-xs text-right mono text-white">${s.stat}</span>
                <div class="flex-1">${bar}</div>
                <span class="w-16 text-right text-sm mono">${ivText}</span>
            </div>`;
        });
        html+='</div>';
        // Summary + Breeding Helper
        const exact=r.results.filter(s=>s.exact);
        const perfect=r.results.filter(s=>s.max_iv===31);
        const good=r.results.filter(s=>s.max_iv!==null&&s.max_iv>=26);
        if(exact.length===6)html+=`<p class="mt-4 text-center text-sm font-bold text-green-400">IVs exacts determines !</p>`;
        else html+=`<p class="mt-4 text-center text-xs text-gray-500">${exact.length}/6 stats exactes. Testez a un niveau different pour affiner.</p>`;

        // Quality tier
        const perfectCount=perfect.length;
        let tier,tierColor,tierIcon;
        if(perfectCount===6){tier='Parfait';tierColor='#76ff03';tierIcon='💎';}
        else if(perfectCount>=5){tier='Competitif';tierColor='#ffd740';tierIcon='⭐';}
        else if(perfectCount>=3){tier='Correct';tierColor='#00e5ff';tierIcon='👍';}
        else if(good.length>=4){tier='Potentiel';tierColor='#90a4ae';tierIcon='📈';}
        else{tier='A ameliorer';tierColor='#ff5252';tierIcon='🔧';}

        html+=`<div class="mt-4 p-4 rounded-lg" style="background:${tierColor}10;border:1px solid ${tierColor}30">
            <div class="flex items-center gap-3 mb-2">
                <span class="text-2xl">${tierIcon}</span>
                <div>
                    <p class="font-bold text-lg" style="color:${tierColor}">${tier}</p>
                    <p class="text-xs text-gray-400">${perfectCount}x31 IV${perfectCount>1?'s':''} ${good.length>perfectCount?`+ ${good.length-perfectCount}x26+`:''}</p>
                </div>
            </div>`;

        // Breeding suggestion
        if(perfectCount<5){
            const statNames=['HP','Atq','Def','A.Spe','D.Spe','Vit'];
            const missing=r.results.filter(s=>s.max_iv===null||s.max_iv<31).map(s=>s.name);
            const target=5-perfectCount;
            // Breeding cost: 2^n parents for n perfect IVs
            const currentParents=Math.pow(2,perfectCount);
            const targetParents=Math.pow(2,5);
            html+=`<div class="mt-2 text-sm">
                <p class="text-gray-300"><span class="font-bold" style="color:#ffd740">Objectif competitif :</span> 5x31 IVs</p>
                <p class="text-xs text-gray-500 mt-1">Stats a ameliorer : ${missing.join(', ')}</p>
                <p class="text-xs text-gray-500">Cout estime : ~<span class="font-bold text-white">${targetParents}</span> parents pour 5x31 (actuellement ${perfectCount}x31 = ~${currentParents} parents)</p>
            </div>`;
        }else if(perfectCount===5){
            // Find the dump stat
            const dump=r.results.find(s=>s.max_iv!==null&&s.max_iv<31);
            if(dump)html+=`<p class="mt-2 text-sm text-gray-300">Stat dump : <span class="font-bold text-white">${dump.name}</span> (${dump.max_iv||'?'}) — ideal pour le competitif si inutile au role</p>`;
        }else if(perfectCount===6){
            html+=`<p class="mt-2 text-sm" style="color:#76ff03">Pokemon parfait 6x31 ! Extreme rarete. Gardez-le precieusement.</p>`;
        }
        html+=`</div>`;
        document.getElementById('iv-results-content').innerHTML=html;
    }catch(e){showToast('Erreur calcul: '+e.message);}
    finally{btn.textContent='Calculer les IVs';btn.disabled=false;}
}
// Populate nature select
(function(){
    const sel=document.getElementById('iv-nature');
    if(!sel)return;
    const natures=Object.entries(TFR).length?null:null; // TFR already loaded
    const NATURES_DATA={
        Hardy:['Hardi','—','—'],Lonely:['Solo','+Atq','-Def'],Brave:['Brave','+Atq','-Vit'],
        Adamant:['Rigide','+Atq','-A.Spe'],Naughty:['Mauvais','+Atq','-D.Spe'],
        Bold:['Assuré','+Def','-Atq'],Docile:['Docile','—','—'],Relaxed:['Relax','+Def','-Vit'],
        Impish:['Malin','+Def','-A.Spe'],Lax:['Lâche','+Def','-D.Spe'],
        Timid:['Timide','+Vit','-Atq'],Hasty:['Pressé','+Vit','-Def'],Serious:['Sérieux','—','—'],
        Jolly:['Jovial','+Vit','-A.Spe'],Naive:['Naïf','+Vit','-D.Spe'],
        Modest:['Modeste','+A.Spe','-Atq'],Mild:['Doux','+A.Spe','-Def'],Quiet:['Discret','+A.Spe','-Vit'],
        Bashful:['Pudique','—','—'],Rash:['Foufou','+A.Spe','-D.Spe'],
        Calm:['Calme','+D.Spe','-Atq'],Gentle:['Gentil','+D.Spe','-Def'],Sassy:['Malpoli','+D.Spe','-Vit'],
        Careful:['Prudent','+D.Spe','-A.Spe'],Quirky:['Bizarre','—','—'],
    };
    Object.entries(NATURES_DATA).forEach(([en,[fr,up,down]])=>{
        const opt=document.createElement('option');opt.value=en;
        opt.textContent=up==='—'?`${fr} (neutre)`:`${fr} (${up} / ${down})`;
        sel.appendChild(opt);
    });
})();

// System diagnostic
async function runDiagnostic(){
    const el=document.getElementById('diagnostic-results');
    el.innerHTML='<p class="text-gray-400">Diagnostic en cours...</p>';
    try{
        const data=await fetch('/api/diagnostic').then(r=>r.json());
        const checks=data.checks;
        const items=[
            {key:'tesseract',label:'Tesseract OCR',icon:'🔍'},
            {key:'fra_language',label:'Langue FR (accents)',icon:'🇫🇷'},
            {key:'game_window',label:'Fenetre PokeMMO',icon:'🎮'},
            {key:'ocr_regions',label:'Zones OCR calibrees',icon:'📐'},
            {key:'dependencies',label:'Dependances Python',icon:'📦'},
        ];
        let html='';
        items.forEach(item=>{
            const c=checks[item.key]||{};
            const ok=c.ok;
            const dot=ok?'🟢':'🔴';
            const detail=ok?(c.version||c.size||`${c.count||''} OK`):(c.error||'Erreur');
            html+=`<div class="flex items-center gap-3 p-2 rounded" style="background:rgba(${ok?'0,200,0':'200,0,0'},0.05)">
                <span>${dot}</span>
                <span class="text-sm font-medium text-white flex-1">${item.icon} ${item.label}</span>
                <span class="text-xs ${ok?'text-green-400':'text-red-400'}">${detail}</span>
            </div>`;
            if(!ok&&c.fix){
                html+=`<div class="ml-8 mb-1 text-[10px] text-gray-500">${c.fix}</div>`;
            }
        });
        const allOk=data.status==='ready';
        html+=`<div class="mt-3 pt-3 border-t border-gray-800 text-center">
            <span class="text-sm font-bold ${allOk?'text-green-400':'text-red-400'}">${allOk?'Systeme pret — overlay OCR fonctionnel':'Des elements manquent — voir ci-dessus'}</span>
        </div>`;
        el.innerHTML=html;
    }catch(e){el.innerHTML=`<p class="text-red-400">Erreur diagnostic: ${e.message}</p>`;}
}

// OCR status check
async function checkOCR(){
    const el=document.getElementById('ocr-status');
    try{
        const[game,ocr]=await Promise.all([fetch('/api/game-status').then(r=>r.json()),fetch('/api/ocr/status').then(r=>r.json())]);
        let h='';
        h+=`<div class="flex justify-between"><span class="text-gray-400">Tesseract</span><span class="${ocr.tesseract_available?'text-green-400':'text-red-400'} font-bold">${ocr.tesseract_available?'Installe':'Non installe'}</span></div>`;
        h+=`<div class="flex justify-between"><span class="text-gray-400">PokeMMO</span><span class="${game.connected?'text-green-400':'text-red-400'} font-bold">${game.connected?'Detecte':'Non detecte'}</span></div>`;
        if(game.connected&&game.window){
            h+=`<div class="flex justify-between"><span class="text-gray-400">Fenetre</span><span class="text-gray-300 mono text-xs">${game.window.width}x${game.window.height}</span></div>`;
            h+=`<div class="flex justify-between"><span class="text-gray-400">Titre</span><span class="text-gray-300 text-xs">${game.title}</span></div>`;
        }
        h+=`<p class="text-xs font-bold text-gray-500 mt-3">ZONES OCR</p>`;
        (ocr.ocr_regions||[]).forEach(r=>{
            h+=`<div class="flex justify-between text-xs"><span class="text-gray-400">${r.name}</span><span class="mono text-gray-300">x:${(r.x*100).toFixed(0)}% y:${(r.y*100).toFixed(0)}% w:${(r.w*100).toFixed(0)}% h:${(r.h*100).toFixed(0)}%</span></div>`;
        });
        if(!ocr.tesseract_available){
            h+=`<p class="text-xs text-red-400 mt-3">⚠ Installe Tesseract OCR : github.com/UB-Mannheim/tesseract/wiki</p>`;
        }
        el.innerHTML=h;
    }catch(e){el.innerHTML='<p class="text-red-400">Erreur: '+e.message+'</p>';}
}

// Pokemon compare
let compareList=[];
function addCompare(id,name,stats){
    if(compareList.length>=3){showToast('Maximum 3 Pokemon');return;}
    if(compareList.find(c=>c.id===id)){showToast('Deja dans la comparaison');return;}
    compareList.push({id,name,stats});
    renderCompare();
    showToast(name+' ajoute a la comparaison');
}
function clearCompare(){compareList=[];document.getElementById('compare-panel').classList.add('hidden');}
function renderCompare(){
    if(compareList.length<2){return;}
    const panel=document.getElementById('compare-panel');
    const content=document.getElementById('compare-content');
    panel.classList.remove('hidden');

    const colors=['#00e5ff','#ff4081','#ffd740'];
    const labels=['HP','Atk','Def','SpA','SpD','Spe'];
    const cx=120,cy=120,r=90,n=6;
    const angle=i=>Math.PI*2*i/n-Math.PI/2;

    // Build overlapped radar SVG
    let svg=`<svg viewBox="0 0 240 240" class="w-64 h-64 mx-auto">`;
    // Grid
    [0.33,0.66,1].forEach(lv=>{let pts='';for(let i=0;i<n;i++){const a=angle(i);pts+=`${cx+r*lv*Math.cos(a)},${cy+r*lv*Math.sin(a)} `;}
        svg+=`<polygon points="${pts}" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>`;});
    // Axes
    for(let i=0;i<n;i++){const a=angle(i);svg+=`<line x1="${cx}" y1="${cy}" x2="${cx+r*Math.cos(a)}" y2="${cy+r*Math.sin(a)}" stroke="rgba(255,255,255,0.05)"/>`;}
    // Labels
    for(let i=0;i<n;i++){const a=angle(i);const lx=cx+(r+16)*Math.cos(a);const ly=cy+(r+16)*Math.sin(a);
        svg+=`<text x="${lx}" y="${ly}" text-anchor="middle" dominant-baseline="middle" fill="#888" font-size="10">${labels[i]}</text>`;}
    // Polygons for each Pokemon
    compareList.forEach((p,pi)=>{
        let pts='';for(let i=0;i<n;i++){const a=angle(i);const v=Math.min(p.stats[i]/255,1);pts+=`${cx+r*v*Math.cos(a)},${cy+r*v*Math.sin(a)} `;}
        svg+=`<polygon points="${pts}" fill="${colors[pi]}20" stroke="${colors[pi]}" stroke-width="2"/>`;
    });
    svg+=`</svg>`;

    // Legend + stats table
    let legend=compareList.map((p,i)=>`<div class="flex items-center gap-2"><div class="w-3 h-3 rounded-full" style="background:${colors[i]}"></div><img src="${spr(p.name)}" class="w-8 h-8"><span class="font-bold text-white text-sm">${p.name_fr||p.name}</span></div>`).join('');

    // Stats comparison table
    let table='<table class="text-sm w-full mt-4"><tr><th class="text-left text-gray-500 text-xs p-1">Stat</th>';
    compareList.forEach((p,i)=>table+=`<th class="text-center p-1" style="color:${colors[i]}">${p.name_fr||p.name}</th>`);
    table+='</tr>';
    labels.forEach((l,li)=>{
        table+=`<tr><td class="text-gray-400 text-xs p-1">${l}</td>`;
        const vals=compareList.map(p=>p.stats[li]);
        const max=Math.max(...vals);
        compareList.forEach((p,pi)=>{
            const v=p.stats[li];
            const isBest=v===max&&vals.filter(x=>x===max).length===1;
            table+=`<td class="text-center p-1 mono ${isBest?'font-black':'text-gray-400'}" style="${isBest?'color:'+colors[pi]:''}">${v}</td>`;
        });
        table+='</tr>';
    });
    // BST row
    table+='<tr class="border-t border-gray-700"><td class="text-gray-400 text-xs p-1 font-bold">BST</td>';
    compareList.forEach((p,i)=>{const bst=p.stats.reduce((a,b)=>a+b,0);table+=`<td class="text-center p-1 mono font-bold" style="color:${colors[i]}">${bst}</td>`;});
    table+='</tr></table>';

    content.innerHTML=`<div class="flex gap-8 items-center"><div>${svg}</div><div class="flex-1"><div class="flex gap-4 mb-3">${legend}</div>${table}</div></div>`;
}

// OCR test capture
async function testOCR(){
    const prev=document.getElementById('ocr-preview');
    prev.classList.remove('hidden');
    document.getElementById('ocr-text-result').textContent='Capture en cours...';
    try{
        const r=await fetch('/api/ocr/capture').then(r=>r.json());
        if(r.error){document.getElementById('ocr-text-result').textContent='Erreur: '+r.error;return;}
        document.getElementById('ocr-preview-img').src=r.preview;
        document.getElementById('ocr-text-result').textContent=r.text||'(rien detecte)';
        document.getElementById('ocr-window-size').textContent='Fenetre: '+r.window_size;
    }catch(e){document.getElementById('ocr-text-result').textContent='Erreur: '+e.message;}
}

// Favorites
function getFavs(){return JSON.parse(localStorage.getItem('favorites')||'[]');}
function isFav(id){return getFavs().includes(id);}
function toggleFav(id){
    let favs=getFavs();
    if(favs.includes(id)){favs=favs.filter(f=>f!==id);showToast('Retire des favoris');}
    else{favs.push(id);showToast('Ajoute aux favoris !');}
    localStorage.setItem('favorites',JSON.stringify(favs));
    // Update button visually
    const btn=event?.target;
    if(btn){btn.textContent=favs.includes(id)?'★ Favori':'☆ Favoris';btn.className=`btn btn-xs mt-2 ${favs.includes(id)?'btn-warning':'btn-ghost'}`;}
}
function filterFavs(){
    const favs=getFavs();
    if(!favs.length){showToast('Aucun favori');return;}
    rDex((window._pk||[]).filter(p=>favs.includes(p.id)));
    document.getElementById('dex-count').textContent=favs.length+' favoris';
}

// Breeding calculator
function calcBreed(){
    const ivs=parseInt(document.getElementById('breed-ivs').value);
    const nature=document.getElementById('breed-nature').value==='yes';
    const costs={1:{parents:2,steps:1,min:5,max:15},2:{parents:4,steps:3,min:30,max:80},3:{parents:8,steps:7,min:100,max:250},4:{parents:16,steps:15,min:300,max:600},5:{parents:32,steps:31,min:800,max:1500},6:{parents:64,steps:63,min:3000,max:8000}};
    const c=costs[ivs]||costs[1];
    const items=nature?'Destiny Knot + Everstone':'Destiny Knot';
    const el=document.getElementById('breed-result');
    el.innerHTML=`
        <div class="grid grid-cols-3 gap-4 text-center mb-3">
            <div class="glass-card p-3"><p class="text-[10px] text-gray-500">PARENTS</p><p class="text-xl font-black mono" style="color:#d500f9">~${c.parents}</p></div>
            <div class="glass-card p-3"><p class="text-[10px] text-gray-500">ETAPES</p><p class="text-xl font-black mono" style="color:#40c4ff">~${c.steps}</p></div>
            <div class="glass-card p-3"><p class="text-[10px] text-gray-500">COUT</p><p class="text-lg font-black mono" style="color:#ffd740">${c.min}k - ${c.max}k</p><p class="text-[9px] text-gray-500">PokéYen</p></div>
        </div>
        <div class="text-sm space-y-1">
            <p class="text-gray-400">Objets : <span class="text-white font-medium">${items}</span></p>
            <p class="text-gray-400">Difficulte : <span class="${ivs>=5?'text-red-400':ivs>=3?'text-yellow-400':'text-green-400'} font-medium">${ivs>=5?'Tres difficile':ivs>=3?'Intermediaire':'Facile'}</span></p>
            ${ivs>=5?'<p class="text-xs text-gray-500 mt-2">💡 Conseil : acheter un 5IV sur le GTL est souvent moins cher que de partir de zero.</p>':''}
        </div>
    `;
}

// Font size
function setFontSize(sz){document.body.style.fontSize=sz+'px';localStorage.setItem('fontSize',sz);showToast('Taille: '+sz+'px');}
const savedFontSize=localStorage.getItem('fontSize');
if(savedFontSize)document.body.style.fontSize=savedFontSize+'px';

// Theme
const THEMES=[
    {id:'night',name:'Night',bg:'#0d1117',accent:'#00e5ff'},
    {id:'dark',name:'Dark',bg:'#1a1a2e',accent:'#e94560'},
    {id:'synthwave',name:'Synthwave',bg:'#2b213a',accent:'#e779c1'},
    {id:'cyberpunk',name:'Cyberpunk',bg:'#1a1a00',accent:'#f7d02c'},
    {id:'dracula',name:'Dracula',bg:'#282a36',accent:'#ff5555'},
    {id:'forest',name:'Forest',bg:'#1a2e1a',accent:'#69f0ae'},
    {id:'luxury',name:'Luxury',bg:'#1a1a1a',accent:'#d4af37'},
    {id:'black',name:'Black',bg:'#000000',accent:'#ffffff'},
];
function setTheme(t){
    document.documentElement.setAttribute('data-theme',t);
    localStorage.setItem('theme',t);
    renderThemePicker();
    const th=THEMES.find(x=>x.id===t);
    const st=document.getElementById('sidebar-theme');
    if(st)st.textContent=th?th.name:t;
    showToast('Theme: '+(th?th.name:t));
}
function renderThemePicker(){
    const el=document.getElementById('theme-picker');
    if(!el)return;
    const current=localStorage.getItem('theme')||'night';
    el.innerHTML=THEMES.map(t=>`<div onclick="setTheme('${t.id}')" class="cursor-pointer text-center transition hover:scale-110" title="${t.name}">
        <div class="w-10 h-10 rounded-full mx-auto mb-1 flex items-center justify-center ${t.id===current?'ring-2 ring-offset-2 ring-offset-dark-800':''}" style="background:${t.bg};border:2px solid ${t.accent};${t.id===current?'ring-color:'+t.accent:''}">
            <div class="w-3 h-3 rounded-full" style="background:${t.accent}"></div>
        </div>
        <p class="text-[9px] ${t.id===current?'text-white font-bold':'text-gray-600'}">${t.name}</p>
    </div>`).join('');
}
renderThemePicker();
(function(){const st=document.getElementById('sidebar-theme');const ct=localStorage.getItem('theme')||'night';const th=THEMES.find(x=>x.id===ct);if(st&&th)st.textContent=th.name;})();
// Restore saved theme
const savedTheme=localStorage.getItem('theme');
if(savedTheme)document.documentElement.setAttribute('data-theme',savedTheme);

// Footer stats
const _appStart=Date.now();
(async function(){
    try{const s=await fetch('/api/stats').then(r=>r.json());
        const fp=document.getElementById('footer-pokemon');
        const fr=document.getElementById('footer-routes');
        if(fp)fp.textContent=(s.total_pokemon||649)+' Pokemon';
        if(fr)fr.textContent=(s.total_routes||0)+' routes';
    }catch(e){}
})();
setInterval(()=>{
    const secs=Math.floor((Date.now()-_appStart)/1000);
    const h=Math.floor(secs/3600),m=Math.floor((secs%3600)/60),s=secs%60;
    const el=document.getElementById('footer-uptime');
    if(el)el.textContent=`Uptime: ${h}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
},1000);

// Keyboard shortcuts
document.addEventListener('keydown',e=>{
    if(e.target.tagName==='INPUT'||e.target.tagName==='TEXTAREA'||e.target.tagName==='SELECT')return;
    const shortcuts={1:'dashboard',2:'pokedex',3:'battle',4:'team',5:'shiny',6:'guide',7:'evtrain',8:'collection',9:'ivcalc',0:'settings'};
    if(shortcuts[e.key])go(shortcuts[e.key]);
    if((e.key==='/'||e.key==='f')&&!e.ctrlKey&&!e.metaKey){e.preventDefault();document.getElementById('global-search')?.focus();}
    if(e.key==='?')toggleHelp();
    if(e.key==='Escape')document.getElementById('help-overlay')?.classList.add('hidden');
});
function toggleHelp(){document.getElementById('help-overlay').classList.toggle('hidden');}

// Natures data (Gen 5 mechanics)
const NATURES=[
    {name:'Hardi',name_en:'Adamant',up:'attack',down:'sp_attack',use:'Sweeper physique'},
    {name:'Rigide',name_en:'Brave',up:'attack',down:'speed',use:'Trick Room physique'},
    {name:'Jovial',name_en:'Jolly',up:'speed',down:'sp_attack',use:'Sweeper rapide physique'},
    {name:'Mauvais',name_en:'Naughty',up:'attack',down:'sp_defense',use:'Attaquant mixte'},
    {name:'Solo',name_en:'Lonely',up:'attack',down:'defense',use:'Attaquant physique fragile'},
    {name:'Modeste',name_en:'Modest',up:'sp_attack',down:'attack',use:'Sweeper special'},
    {name:'Doux',name_en:'Mild',up:'sp_attack',down:'defense',use:'Attaquant special fragile'},
    {name:'Discret',name_en:'Quiet',up:'sp_attack',down:'speed',use:'Trick Room special'},
    {name:'Foufou',name_en:'Rash',up:'sp_attack',down:'sp_defense',use:'Attaquant special mixte'},
    {name:'Timide',name_en:'Timid',up:'speed',down:'attack',use:'Sweeper rapide special'},
    {name:'Presse',name_en:'Hasty',up:'speed',down:'defense',use:'Rapide fragile'},
    {name:'Naif',name_en:'Naive',up:'speed',down:'sp_defense',use:'Rapide mixte'},
    {name:'Assure',name_en:'Bold',up:'defense',down:'attack',use:'Wall physique'},
    {name:'Relax',name_en:'Relaxed',up:'defense',down:'speed',use:'Tank physique lent'},
    {name:'Malin',name_en:'Impish',up:'defense',down:'sp_attack',use:'Wall physique'},
    {name:'Lache',name_en:'Lax',up:'defense',down:'sp_defense',use:'Def physique uniquement'},
    {name:'Calme',name_en:'Calm',up:'sp_defense',down:'attack',use:'Wall special'},
    {name:'Gentil',name_en:'Gentle',up:'sp_defense',down:'defense',use:'Def speciale uniquement'},
    {name:'Malpoli',name_en:'Sassy',up:'sp_defense',down:'speed',use:'Tank special lent'},
    {name:'Prudent',name_en:'Careful',up:'sp_defense',down:'sp_attack',use:'Wall special'},
    {name:'Docile',name_en:'Docile',up:null,down:null,use:'Neutre'},
    {name:'Bizarre',name_en:'Quirky',up:null,down:null,use:'Neutre'},
    {name:'Serieux',name_en:'Serious',up:null,down:null,use:'Neutre'},
    {name:'Pudique',name_en:'Bashful',up:null,down:null,use:'Neutre'},
    {name:'Hardy',name_en:'Hardy',up:null,down:null,use:'Neutre'},
];
const STAT_NAMES={attack:'Attaque',defense:'Defense',sp_attack:'Att. Spe',sp_defense:'Def. Spe',speed:'Vitesse'};
const STAT_COLORS={attack:'#F08030',defense:'#F8D030',sp_attack:'#6890F0',sp_defense:'#78C850',speed:'#F85888'};

function renderNatures(list){
    const el=document.getElementById('natures-table');
    let h='<table class="w-full text-sm"><thead><tr>';
    h+='<th class="text-left p-2 text-gray-500 text-xs">Nature</th>';
    h+='<th class="text-left p-2 text-gray-500 text-xs">EN</th>';
    h+='<th class="text-center p-2 text-xs" style="color:#69f0ae">+10%</th>';
    h+='<th class="text-center p-2 text-xs" style="color:#ff5252">-10%</th>';
    h+='<th class="text-left p-2 text-gray-500 text-xs">Usage</th>';
    h+='</tr></thead><tbody>';
    list.forEach(n=>{
        const upTxt=n.up?STAT_NAMES[n.up]:'—';
        const downTxt=n.down?STAT_NAMES[n.down]:'—';
        const upClr=n.up?STAT_COLORS[n.up]:'#888';
        const downClr=n.down?STAT_COLORS[n.down]:'#888';
        const isNeutral=!n.up;
        h+=`<tr class="border-b border-gray-800/50 hover:bg-dark-600/30">`;
        h+=`<td class="p-2 font-bold ${isNeutral?'text-gray-500':'text-white'}">${n.name}</td>`;
        h+=`<td class="p-2 text-gray-600 text-xs">${n.name_en}</td>`;
        h+=`<td class="p-2 text-center font-bold" style="color:${upClr}">${isNeutral?'—':'↑ '+upTxt}</td>`;
        h+=`<td class="p-2 text-center font-bold" style="color:${isNeutral?'#888':downClr}">${isNeutral?'—':'↓ '+downTxt}</td>`;
        h+=`<td class="p-2 text-gray-400 text-xs">${n.use}</td>`;
        h+=`</tr>`;
    });
    h+='</tbody></table>';
    el.innerHTML=h;
}
function filterNatures(){
    const f=document.getElementById('nature-filter').value;
    if(!f){renderNatures(NATURES);return;}
    if(f==='neutral'){renderNatures(NATURES.filter(n=>!n.up));return;}
    renderNatures(NATURES.filter(n=>n.up===f));
}

// Recommend natures for a Pokemon based on stats
function recommendNatures(p){
    const stats={attack:p.attack,defense:p.defense,sp_attack:p.sp_attack,sp_defense:p.sp_defense,speed:p.speed};
    const sorted=Object.entries(stats).sort((a,b)=>b[1]-a[1]);
    const topStat=sorted[0][0]; // highest stat
    const lowStat=sorted[sorted.length-1][0]; // lowest stat
    // Find natures that boost the top stat
    const good=NATURES.filter(n=>n.up===topStat).sort((a,b)=>{
        // Prefer natures that lower the least useful stat
        const aScore=stats[a.down]||999;
        const bScore=stats[b.down]||999;
        return aScore-bScore;
    });
    // Best nature = boost top, lower bottom
    const best=good.length?good[0]:null;
    // Secondary: speed nature if speed is decent
    const speedNature=NATURES.find(n=>n.up==='speed'&&n.down===(p.attack>p.sp_attack?'sp_attack':'attack'));
    return {best,speedNature,all:good.slice(0,3)};
}

// Horde Optimizer
async function loadHordes(){
    const region=document.getElementById('horde-region')?.value||'';
    const type=document.getElementById('horde-type')?.value||'';
    const pokemon=document.getElementById('horde-search')?.value||'';
    try{
        let url='/api/hordes?';
        if(region)url+=`region=${region}&`;
        if(type)url+=`poke_type=${type}&`;
        if(pokemon&&pokemon.length>=2)url+=`pokemon=${pokemon}&`;
        const data=await fetch(url).then(r=>r.json());
        const el=document.getElementById('horde-list');
        const cnt=document.getElementById('horde-count');
        if(cnt)cnt.textContent=`${data.length} spots`;
        if(!data.length){el.innerHTML='<p class="text-gray-600 italic text-sm">Aucun spot trouve.</p>';return;}
        // Group by route
        const byRoute={};
        data.forEach(h=>{
            const key=h.route_name+' ('+h.region+')';
            if(!byRoute[key])byRoute[key]={route:h.route_name,region:h.region,pokemon:[]};
            byRoute[key].pokemon.push(h);
        });
        el.innerHTML=Object.values(byRoute).map(group=>{
            const regionClr={Kanto:'#40c4ff',Johto:'#ffd740',Hoenn:'#69f0ae',Sinnoh:'#d500f9',Unova:'#ff6e40'}[group.region]||'#888';
            return `<div class="glass-card p-3 mb-2">
                <div class="flex items-center gap-2 mb-2">
                    <span class="text-[10px] px-2 py-0.5 rounded font-bold" style="background:${regionClr}20;color:${regionClr}">${group.region}</span>
                    <span class="font-bold text-white text-sm">${group.route}</span>
                    <span class="text-[10px] text-gray-600 ml-auto">${group.pokemon.length} Pokemon</span>
                </div>
                <div class="flex flex-wrap gap-2">${group.pokemon.map(p=>`<div class="flex items-center gap-1.5 px-2 py-1 rounded" style="background:rgba(255,255,255,0.03)">
                    <img src="${spr(p.name)}" data-id="${p.pokemon_id}" class="w-6 h-6 sprite-hover" loading="lazy">
                    <span class="text-xs text-white">${p.name_fr||p.name}</span>
                    ${pill(p.type1)}${p.type2?' '+pill(p.type2):''}
                    <span class="text-[10px] text-gray-500">Lv.${p.level_min}-${p.level_max}</span>
                </div>`).join('')}</div>
            </div>`;
        }).join('');
    }catch(e){console.error(e);}
}

async function loadHordeSummary(){
    try{
        const data=await fetch('/api/hordes/summary').then(r=>r.json());
        const el=document.getElementById('horde-summary');
        const regionClr={Kanto:'#40c4ff',Johto:'#ffd740',Hoenn:'#69f0ae',Sinnoh:'#d500f9',Unova:'#ff6e40'};
        el.innerHTML=data.map(r=>`<div class="glass-card p-3 text-center cursor-pointer hover:border-white/20" onclick="document.getElementById('horde-region').value='${r.region}';loadHordes();">
            <p class="text-[10px] font-bold tracking-widest" style="color:${regionClr[r.region]||'#888'}">${r.region.toUpperCase()}</p>
            <p class="text-lg font-black text-white mono">${r.pokemon_count}</p>
            <p class="text-[10px] text-gray-500">${r.route_count} routes</p>
        </div>`).join('');
        // Total for stats
        const total=data.reduce((a,r)=>a+r.pokemon_count,0);
        const routes=data.reduce((a,r)=>a+r.route_count,0);
        const st=document.getElementById('horde-stats');
        if(st)st.innerHTML=`<span class="mono font-bold text-white">${total}</span> Pokemon<br><span class="mono">${routes}</span> routes`;
    }catch(e){}
    // Populate type filter
    const sel=document.getElementById('horde-type');
    if(sel&&sel.options.length<=1){
        Object.keys(TC).forEach(t=>{sel.innerHTML+=`<option value="${t}">${tfr(t)}</option>`;});
    }
}

function calcSS(){
    const pp=parseInt(document.getElementById('ss-pp')?.value||5);
    const mons=parseInt(document.getElementById('ss-mons')?.value||2);
    const leppa=document.getElementById('ss-leppa')?.value==='yes';
    const totalPP=pp*mons;
    const encountersPerPP=5; // 5 Pokemon per horde
    const timePerHorde=30; // ~30 seconds per horde encounter
    const totalEncounters=leppa?Infinity:totalPP*encountersPerPP;
    const totalTime=leppa?'Infini':Math.round(totalPP*timePerHorde/60)+' min';
    const rate=30000; // base shiny rate
    const effRate=Math.round(rate/encountersPerPP); // effective rate with hordes
    const prob=leppa?'-':((1-Math.pow(1-1/rate,totalEncounters))*100).toFixed(2)+'%';
    const el=document.getElementById('ss-result');
    el.innerHTML=`<div class="grid grid-cols-4 gap-3 text-center">
        <div><p class="text-[10px] text-gray-500">TOTAL PP</p><p class="font-bold mono text-white">${leppa?'∞':totalPP}</p></div>
        <div><p class="text-[10px] text-gray-500">RENCONTRES</p><p class="font-bold mono" style="color:#40c4ff">${leppa?'∞':totalEncounters}</p></div>
        <div><p class="text-[10px] text-gray-500">DUREE</p><p class="font-bold mono" style="color:#ffd740">${totalTime}</p></div>
        <div><p class="text-[10px] text-gray-500">TAUX EFF.</p><p class="font-bold mono" style="color:#69f0ae">~1/${effRate.toLocaleString()}</p></div>
    </div>
    <p class="text-xs text-gray-500 mt-2">Avec Leppa Berry + Pickup, tu peux chasser indefiniment. 5 Pokemon par horde = taux shiny effectif 5x meilleur.</p>`;
}

// EV Training (with localStorage persistence)
function updateEVTracker(){
    const stats=['hp','attack','defense','sp_attack','sp_defense','speed'];
    let total=0;
    const evData={};
    stats.forEach(s=>{
        const v=parseInt(document.getElementById('ev-t-'+s)?.value||0);
        evData[s]=v;
        total+=v;
        const bar=document.getElementById('ev-b-'+s);
        if(bar)bar.style.width=(v/252*100)+'%';
    });
    const el=document.getElementById('ev-total');
    if(el){el.textContent=total;el.style.color=total>510?'#ff5252':total===510?'#69f0ae':'#fff';}
    const bar=document.getElementById('ev-total-bar');
    if(bar){bar.style.width=(Math.min(total,510)/510*100)+'%';bar.style.background=total>510?'#ff5252':'#00e5ff';}
    localStorage.setItem('ev_tracker',JSON.stringify(evData));
}
function loadEVTracker(){
    const saved=JSON.parse(localStorage.getItem('ev_tracker')||'{}');
    const stats=['hp','attack','defense','sp_attack','sp_defense','speed'];
    stats.forEach(s=>{const el=document.getElementById('ev-t-'+s);if(el&&saved[s]!==undefined)el.value=saved[s];});
    updateEVTracker();
}
function presetEV(preset){
    const stats=['hp','attack','defense','sp_attack','sp_defense','speed'];
    const presets={
        'sweeper_phy':{attack:252,speed:252,hp:6},
        'sweeper_spe':{sp_attack:252,speed:252,hp:6},
        'tank':{hp:252,defense:252,sp_defense:6},
        'sp_wall':{hp:252,sp_defense:252,defense:6},
        'bulky_atk':{hp:252,attack:252,speed:6},
        'reset':{}
    };
    const p=presets[preset]||{};
    stats.forEach(s=>{const el=document.getElementById('ev-t-'+s);if(el)el.value=p[s]||0;});
    updateEVTracker();
    if(preset!=='reset')showToast('Preset applique');
}

async function loadEVSpots(stat){
    window._evStat=stat;
    const region=document.getElementById('ev-region')?.value||'';
    const method=document.getElementById('ev-method')?.value||'';
    const el=document.getElementById('ev-spots');
    const cnt=document.getElementById('ev-spot-count');
    const statName={'hp':'HP','attack':'Attaque','defense':'Defense','sp_attack':'Att. Spe','sp_defense':'Def. Spe','speed':'Vitesse'}[stat]||stat;
    const statClr={'hp':'#78C850','attack':'#F08030','defense':'#F8D030','sp_attack':'#6890F0','sp_defense':'#78C850','speed':'#F85888'}[stat]||'#888';
    try{
        let url=`/api/ev-spots/${stat}?`;
        if(region)url+=`region=${region}&`;
        if(method)url+=`method=${method}&`;
        const data=await fetch(url).then(r=>r.json());
        if(data.error){el.innerHTML=`<p class="text-red-400">${data.error}</p>`;return;}
        if(cnt)cnt.textContent=`${data.length} spots — ${statName}`;
        if(!data.length){el.innerHTML='<p class="text-gray-600 italic">Aucun spot trouve.</p>';return;}
        // Group by route for cleaner display
        const evKey='ev_'+stat;
        el.innerHTML=data.map(s=>{
            const evVal=s[evKey]||0;
            const methodIcon={horde:'🌊',walking:'🌿',surfing:'🏄',fishing_old:'🎣'}[s.method]||'📍';
            const isHorde=s.method==='horde';
            const regionClr={Kanto:'#40c4ff',Johto:'#ffd740',Hoenn:'#69f0ae',Sinnoh:'#d500f9',Unova:'#ff6e40'}[s.region]||'#888';
            return `<div class="flex items-center gap-3 p-2 rounded hover:bg-dark-600/30 ${isHorde?'border-l-2':'border-l border-transparent'}" style="${isHorde?'border-color:#d500f9':''}">
                <img src="${spr(s.name)}" data-id="${s.pokemon_id}" class="w-8 h-8 sprite-hover" loading="lazy">
                <span class="font-bold text-white text-sm w-24">${s.name_fr||s.name}</span>
                ${pill(s.type1)}
                <span class="mono font-bold text-sm" style="color:${statClr}">+${evVal}</span>
                <span class="text-[10px] ${isHorde?'font-bold':'text-gray-500'}" style="${isHorde?'color:#d500f9':''}">${methodIcon} ${isHorde?'Horde (x5)':s.method==='surfing'?'Surf':s.method==='walking'?'Herbe':s.method}</span>
                <span class="text-xs text-gray-400 flex-1">${s.route_name_fr||s.route_name}</span>
                <span class="text-[10px] px-1.5 py-0.5 rounded" style="background:${regionClr}15;color:${regionClr}">${s.region}</span>
                <span class="text-[10px] text-gray-600">Lv.${s.level_min}-${s.level_max}</span>
            </div>`;
        }).join('');
    }catch(e){el.innerHTML='<p class="text-red-400">Erreur: '+e.message+'</p>';}
}

// Ability FR translations
let AFR={};
async function loadAbilityFR(){try{AFR=await fetch('/api/abilities/translations').then(r=>r.json());}catch(e){}}
const afr=a=>AFR[a]||a; // Translate ability EN->FR

// Ability viewer
async function showAbility(ability){
    try{
        const data=await fetch(`/api/abilities/${encodeURIComponent(ability)}`).then(r=>r.json());
        if(!data.length){showToast('Aucun Pokemon avec '+ability);return;}
        const d=document.getElementById('dex-detail');
        const g=document.getElementById('dex-grid');
        g.classList.add('hidden');d.classList.remove('hidden');
        d.innerHTML=`<button onclick="closeDex()" class="text-sm mb-4 font-medium" style="color:#00e5ff">← Retour au Pokedex</button>
        <div class="glass-card p-6">
            <div class="flex items-center gap-3 mb-4">
                <p class="text-xl font-black text-white">${afr(ability)}</p>
                <span class="text-xs text-gray-500">${ability}</span>
                <span class="text-xs px-2 py-1 rounded" style="background:rgba(0,229,255,0.1);color:#00e5ff">${data.length} Pokemon</span>
            </div>
            <div class="grid grid-cols-3 sm:grid-cols-5 md:grid-cols-7 gap-2">
                ${data.map(p=>{
                    const isHA=p.ability_type==='hidden';
                    return `<div class="dex-card ${isHA?'':'border-l-2'}" style="${isHA?'border-color:#d500f9':'border-color:#00e5ff'};border-bottom:3px solid ${TC[p.type1]||'#888'}" onclick="showP(${p.id})">
                        <img src="${spr(p.name)}" data-id="${p.id}" class="w-12 h-12 mx-auto sprite-hover" loading="lazy">
                        <p class="text-[10px] font-bold text-white mt-1">${p.name_fr||p.name}</p>
                        <p class="text-[9px] ${isHA?'':'text-gray-600'}" style="${isHA?'color:#d500f9':''}">${isHA?'HA':'Normal'}</p>
                    </div>`;
                }).join('')}
            </div>
        </div>`;
    }catch(e){console.error(e);}
}

// Dashboard route search
async function dashRouteSearch(q){
    const el=document.getElementById('dash-route-results');
    if(q.length<2){el.classList.add('hidden');return;}
    try{
        const region=document.getElementById('dash-region')?.value||'';
        const routes=await fetch(`/api/routes?region=${region}`).then(r=>r.json());
        const filtered=routes.filter(r=>(r.display_name||r.name).toLowerCase().includes(q.toLowerCase())||r.name.toLowerCase().includes(q.toLowerCase())).slice(0,8);
        if(!filtered.length){el.classList.add('hidden');return;}
        el.classList.remove('hidden');
        el.innerHTML=filtered.map(r=>{const dn=r.display_name||r.name;return `<div class="px-2 py-1.5 rounded cursor-pointer text-xs hover:bg-dark-600 flex justify-between" onclick="dashSelectRoute('${r.name.replace(/'/g,"\\'")}','${r.region}')"><span class="text-white">${dn}</span><span class="text-gray-600">${r.region}</span></div>`;}).join('');
    }catch(e){el.classList.add('hidden');}
}
async function dashSelectRoute(name,region){
    document.getElementById('dash-route-results').classList.add('hidden');
    document.getElementById('dash-route-search').value='';
    document.getElementById('loc-route').textContent=name.toUpperCase();
    document.getElementById('spawn-subtitle').textContent=`${name} (${region})`;
    try{
        const sp=await fetch(`/api/spawns/${encodeURIComponent(name)}?region=${region}`).then(r=>r.json());
        const sl=document.getElementById('spawns-list');
        if(Array.isArray(sp)&&sp.length){
            sl.innerHTML=sp.slice(0,8).map(s=>`<div class="spawn-row"><img src="${spr(s.pokemon_name)}" data-id="${s.pokemon_id}" class="w-8 h-8 sprite-hover"><span class="font-semibold text-white text-sm flex-1">${s.pokemon_name}</span>${pill(s.type1)}${s.type2?' '+pill(s.type2):''}<div class="stat-track w-20"><div class="stat-fill bg-neon-green" style="width:${Math.min(s.rate,100)}%"></div></div><span class="mono text-xs text-gray-400">${s.rate.toFixed(0)}%</span><span class="text-xs text-gray-500">Lv.${s.level_min}-${s.level_max}</span></div>`).join('');
        }else{sl.innerHTML='<p class="text-gray-600 text-sm italic">Aucun spawn trouve.</p>';}
    }catch(e){console.error(e);}
}
async function dashLoadRoute(){
    // Load a random route from the selected region
    const region=document.getElementById('dash-region')?.value||'Kanto';
    try{
        const routes=await fetch(`/api/routes?region=${region}`).then(r=>r.json());
        if(routes.length){
            const r=routes[Math.floor(Math.random()*routes.length)];
            dashSelectRoute(r.name,r.region);
        }
    }catch(e){}
}

// Move filter for Pokedex detail
function filterMoves(method){
    document.querySelectorAll('.move-row').forEach(r=>{
        r.style.display=(!method||r.dataset.method===method)?'':'none';
    });
}

// OCR Debug Studio
let ocrImage=null;
let ocrRegions=[];

async function ocrLoadRegions(){
    try{const data=await fetch('/api/ocr/regions').then(r=>r.json());
    ocrRegions=data.regions||[];ocrRenderRegions();}catch(e){
    ocrRegions=[
        {id:'route_name',label:'Nom de Route',x:1,y:0,w:20,h:4,color:'#00e5ff'},
        {id:'opponent_name',label:'Nom Adversaire',x:5,y:6,w:25,h:5,color:'#ff4081'},
    ];ocrRenderRegions();}
}

async function ocrCaptureGame(){
    showToast('Capture en cours...');
    try{
        const r=await fetch('/api/ocr/capture-game').then(r=>r.json());
        if(!r.available){showToast(r.error||'Erreur capture');return;}
        // Ensure default regions exist
        if(!ocrRegions||ocrRegions.length===0){
            ocrRegions=[
                {id:'route_name',label:'Nom de Route',x:1,y:0,w:20,h:4,color:'#00e5ff'},
                {id:'opponent_name',label:'Nom Adversaire',x:5,y:6,w:25,h:5,color:'#ff4081'},
            ];
        }
        const img=new Image();
        img.onload=function(){
            ocrImage=r.image;
            const canvas=document.getElementById('ocr-canvas');
            const ctx=canvas.getContext('2d');
            const wrap=document.getElementById('ocr-canvas-wrap');
            const maxW=wrap.clientWidth;
            const scale=maxW/img.width;
            canvas.width=maxW;canvas.height=img.height*scale;
            ctx.drawImage(img,0,0,canvas.width,canvas.height);
            canvas.style.display='block';
            document.getElementById('ocr-placeholder').style.display='none';
            document.getElementById('ocr-regions-overlay').style.display='block';
            ocrDrawRegions();
            ocrRenderRegions();
            const testAllBtn=document.getElementById('ocr-test-all-btn');
            if(testAllBtn)testAllBtn.disabled=false;
            showToast(`PokeMMO capture : ${r.width}x${r.height} — Deplace les zones sur le texte du jeu`);
        };
        img.src=r.image;
    }catch(e){showToast('Erreur: '+e.message);}
}

function ocrUpload(ev){
    const file=ev.target.files[0];if(!file)return;
    const reader=new FileReader();
    reader.onload=function(e){
        const img=new Image();
        img.onload=function(){
            ocrImage=e.target.result;
            const canvas=document.getElementById('ocr-canvas');
            const ctx=canvas.getContext('2d');
            // Scale to fit container width
            const wrap=document.getElementById('ocr-canvas-wrap');
            const maxW=wrap.clientWidth;
            const scale=maxW/img.width;
            canvas.width=maxW;canvas.height=img.height*scale;
            ctx.drawImage(img,0,0,canvas.width,canvas.height);
            canvas.style.display='block';
            document.getElementById('ocr-placeholder').style.display='none';
            document.getElementById('ocr-regions-overlay').style.display='block';
            ocrDrawRegions();
            const testAllBtn=document.getElementById('ocr-test-all-btn');
            if(testAllBtn)testAllBtn.disabled=false;
            showToast(`Screenshot charge : ${img.width}x${img.height}`);
        };
        img.src=e.target.result;
    };
    reader.readAsDataURL(file);
}

function ocrDrawRegions(){
    const canvas=document.getElementById('ocr-canvas');
    if(!canvas||!ocrImage)return;
    const overlay=document.getElementById('ocr-regions-overlay');
    overlay.innerHTML='';
    const cw=canvas.width,ch=canvas.height;
    ocrRegions.forEach((r,i)=>{
        const left=r.x/100*cw,top=r.y/100*ch,w=r.w/100*cw,h=r.h/100*ch;
        overlay.innerHTML+=`<div style="position:absolute;left:${left}px;top:${top}px;width:${w}px;height:${h}px;border:2px solid ${r.color};background:${r.color}15;pointer-events:auto;cursor:move" class="ocr-region" data-idx="${i}" title="${r.label}">
            <span style="position:absolute;top:-16px;left:0;font-size:9px;color:${r.color};white-space:nowrap;font-weight:700">${r.label}</span>
        </div>`;
    });
    // Make regions draggable
    overlay.querySelectorAll('.ocr-region').forEach(el=>{
        let startX,startY,origX,origY;
        el.onmousedown=function(e){
            e.preventDefault();
            const idx=parseInt(el.dataset.idx);
            startX=e.clientX;startY=e.clientY;
            origX=ocrRegions[idx].x;origY=ocrRegions[idx].y;
            const onMove=function(e2){
                const dx=(e2.clientX-startX)/cw*100;
                const dy=(e2.clientY-startY)/ch*100;
                ocrRegions[idx].x=Math.max(0,Math.min(100-ocrRegions[idx].w,origX+dx));
                ocrRegions[idx].y=Math.max(0,Math.min(100-ocrRegions[idx].h,origY+dy));
                ocrDrawRegions();ocrRenderRegions();
            };
            const onUp=function(){document.removeEventListener('mousemove',onMove);document.removeEventListener('mouseup',onUp);};
            document.addEventListener('mousemove',onMove);
            document.addEventListener('mouseup',onUp);
        };
    });
}

function ocrRenderRegions(){
    const el=document.getElementById('ocr-region-list');
    el.innerHTML=ocrRegions.map((r,i)=>`<div class="flex items-center gap-2 p-2 rounded" style="background:${r.color}08;border-left:3px solid ${r.color}">
        <div class="w-3 h-3 rounded-full flex-shrink-0" style="background:${r.color}"></div>
        <input type="text" value="${r.label}" onchange="ocrRegions[${i}].label=this.value;ocrDrawRegions()" class="input input-bordered input-xs flex-1 text-xs">
        <span class="text-[10px] text-gray-500 mono">x:${r.x.toFixed(0)}% y:${r.y.toFixed(0)}%</span>
        <span class="text-[10px] text-gray-500 mono">w:${r.w.toFixed(0)}% h:${r.h.toFixed(0)}%</span>
        <input type="number" value="${r.w.toFixed(0)}" min="1" max="80" class="input input-bordered input-xs w-12 text-center" onchange="ocrRegions[${i}].w=parseFloat(this.value);ocrDrawRegions()">
        <input type="number" value="${r.h.toFixed(0)}" min="1" max="80" class="input input-bordered input-xs w-12 text-center" onchange="ocrRegions[${i}].h=parseFloat(this.value);ocrDrawRegions()">
        <button onclick="ocrTestRegion(${i})" class="btn btn-xs btn-warning" ${ocrImage?'':'disabled'}>Tester</button>
        <button onclick="ocrRegions.splice(${i},1);ocrDrawRegions();ocrRenderRegions()" class="btn btn-xs btn-ghost text-gray-600 hover:text-red-400">✕</button>
    </div>`).join('');
}

function goIVCalc(id,name){
    ivSelectPokemon(id,name);
    go('ivcalc');
}
async function ocrDetectResolution(){
    try{
        const d=await fetch('/api/ocr/detect-resolution').then(r=>r.json());
        if(d.detected){
            showToast(`PokeMMO detecte: ${d.resolution}. Preset suggere: ${d.suggested_preset}`);
            ocrApplyPreset(d.suggested_preset);
        }
    }catch(e){}
}
function ocrApplyPreset(res){
    // Pre-calibrated zone positions from ladyd_'s screenshots (2026-04-02)
    // Percentages relative to game window
    const presets={
        '1920x1080':{route:{x:0.5,y:0,w:15,h:3},opponent:{x:5,y:5,w:20,h:4}},
        '1920x1040':{route:{x:0.5,y:0,w:15,h:3},opponent:{x:5,y:5,w:20,h:4}},
        '1280x720':{route:{x:0.5,y:0,w:16,h:3.5},opponent:{x:5,y:5.5,w:22,h:4.5}},
    };
    const p=presets[res];
    if(!p){showToast('Preset inconnu: '+res);return;}
    ocrRegions=[
        {id:'route_name',label:'Nom de Route',x:p.route.x,y:p.route.y,w:p.route.w,h:p.route.h,color:'#00e5ff'},
        {id:'opponent_name',label:'Nom Adversaire',x:p.opponent.x,y:p.opponent.y,w:p.opponent.w,h:p.opponent.h,color:'#ff4081'},
    ];
    ocrDrawRegions();ocrRenderRegions();
    // Auto-save
    ocrSaveRegions();
    showToast('Preset '+res+' applique et sauvegarde !');
}
function ocrAddRegion(){
    const colors=['#00e5ff','#ff4081','#ffd740','#69f0ae','#ff6e40','#d500f9','#40c4ff'];
    ocrRegions.push({id:'zone_'+Date.now(),label:'Nouvelle zone',x:10,y:10,w:15,h:4,color:colors[ocrRegions.length%colors.length]});
    ocrDrawRegions();ocrRenderRegions();
}

function ocrResetRegions(){
    ocrRegions=[
        {id:'route_name',label:'Nom de Route',x:1,y:1,w:18,h:4,color:'#00e5ff'},
        {id:'opponent_name',label:'Nom Adversaire',x:52,y:5,w:35,h:4,color:'#ff4081'},
        {id:'opponent_level',label:'Niveau Adversaire',x:80,y:5,w:12,h:4,color:'#ffd740'},
        {id:'player_hp',label:'HP Joueur',x:55,y:75,w:20,h:3,color:'#69f0ae'},
        {id:'opponent_hp',label:'HP Adversaire',x:55,y:12,w:20,h:3,color:'#ff6e40'},
    ];
    ocrDrawRegions();ocrRenderRegions();showToast('Zones reinitialises');
}

async function ocrSaveRegions(){
    try{await fetch('/api/ocr/regions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({regions:ocrRegions})});
    showToast('Zones sauvegardees ! L\'overlay utilisera ces reglages.');
    }catch(e){showToast('Erreur sauvegarde');}
}

async function ocrTestAll(){
    if(!ocrImage){showToast('Charge un screenshot d\'abord');return;}
    const resEl=document.getElementById('ocr-test-results');
    const listEl=document.getElementById('ocr-results-list');
    resEl.classList.remove('hidden');
    listEl.innerHTML='<p class="text-gray-500">Test OCR sur toutes les zones...</p>';
    let html='';
    for(let i=0;i<ocrRegions.length;i++){
        const r=ocrRegions[i];
        try{
            const res=await fetch('/api/ocr/test-region',{method:'POST',headers:{'Content-Type':'application/json'},
                body:JSON.stringify({image:ocrImage,x:r.x,y:r.y,w:r.w,h:r.h})}).then(r=>r.json());
            html+=`<div class="flex items-center gap-3 p-2 rounded" style="border-left:3px solid ${r.color}">
                <div class="w-3 h-3 rounded-full" style="background:${r.color}"></div>
                <span class="text-sm text-gray-400 w-32">${r.label}</span>
                <span class="font-bold text-white">${res.text}</span>
                ${!res.available?'<span class="text-[10px] text-yellow-400">(Tesseract non dispo)</span>':''}
            </div>`;
            // If opponent detected, show combat preview
            if(r.id==='opponent_name'&&res.text&&res.available&&!res.text.startsWith('(')){
                const match=await fetch(`/api/pokemon/search/${encodeURIComponent(res.text)}`).then(r=>r.json());
                if(Array.isArray(match)&&match.length)ocrShowCombatPreview(match[0]);
            }
        }catch(e){html+=`<div class="text-red-400 text-xs">Erreur zone ${r.label}</div>`;}
    }
    listEl.innerHTML=html||'<p class="text-gray-500">Aucun resultat</p>';
}

function ocrExportConfig(){
    const data=JSON.stringify({regions:ocrRegions,exported:new Date().toISOString()},null,2);
    const blob=new Blob([data],{type:'application/json'});
    const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='pokemmo-ocr-config.json';a.click();
    showToast('Config OCR exportee !');
}

function ocrImportConfig(ev){
    const file=ev.target.files[0];if(!file)return;
    const reader=new FileReader();
    reader.onload=function(e){
        try{
            const data=JSON.parse(e.target.result);
            if(data.regions&&Array.isArray(data.regions)){
                ocrRegions=data.regions;
                ocrDrawRegions();ocrRenderRegions();
                showToast(`Config importee : ${ocrRegions.length} zones`);
            }
        }catch(err){showToast('Erreur : fichier invalide');}
    };
    reader.readAsText(file);
}

async function ocrTestRegion(idx){
    if(!ocrImage){showToast('Charge un screenshot d\'abord');return;}
    const r=ocrRegions[idx];
    const resEl=document.getElementById('ocr-test-results');
    const listEl=document.getElementById('ocr-results-list');
    resEl.classList.remove('hidden');
    listEl.innerHTML=`<p class="text-gray-500">Test OCR sur "${r.label}"...</p>`;
    try{
        const res=await fetch('/api/ocr/test-region',{method:'POST',headers:{'Content-Type':'application/json'},
            body:JSON.stringify({image:ocrImage,x:r.x,y:r.y,w:r.w,h:r.h})}).then(r=>r.json());
        let html=`<div class="flex items-center gap-3 p-2 rounded" style="border-left:3px solid ${r.color}">
            <div class="w-3 h-3 rounded-full" style="background:${r.color}"></div>
            <span class="text-sm text-gray-400">${r.label}</span>
            <span class="font-bold text-white">${res.text}</span>
            ${!res.available?'<span class="text-[10px] text-yellow-400">(Tesseract non dispo sur ce serveur)</span>':''}
        </div>`;
        // If this is the opponent name, try to match a Pokemon
        if(r.id==='opponent_name'&&res.text&&res.available&&!res.text.startsWith('(')){
            const match=await fetch(`/api/pokemon/search/${encodeURIComponent(res.text)}`).then(r=>r.json());
            if(Array.isArray(match)&&match.length){
                const p=match[0];
                html+=`<div class="glass-card p-3 mt-2"><p class="text-xs text-gray-500 mb-1">POKEMON DETECTE</p>
                <div class="flex items-center gap-3"><img src="${spr(p.name)}" data-id="${p.id}" class="w-12 h-12">
                <div><p class="font-bold text-white">${p.name_fr||p.name}</p><div class="flex gap-1">${pill(p.type1)}${p.type2?' '+pill(p.type2):''}</div></div></div></div>`;
                // Show in combat preview
                ocrShowCombatPreview(p);
            }
        }
        listEl.innerHTML=html;
    }catch(e){listEl.innerHTML=`<p class="text-red-400">Erreur: ${e.message}</p>`;}
}

async function ocrShowCombatPreview(p){
    const el=document.getElementById('combat-ocr-preview');
    const bst=p.hp+p.attack+p.defense+p.sp_attack+p.sp_defense+p.speed;
    // Calculate weaknesses from type chart
    try{
        const chartData=await fetch('/api/type-chart').then(r=>r.json());
        const ts=chartData.types,ch=chartData.chart;
        const defTypes=[p.type1];if(p.type2)defTypes.push(p.type2);
        const weak4x=[],weak2x=[],resist05=[],immune=[];
        ts.forEach(atk=>{
            let m=1;defTypes.forEach(dt=>{m*=(ch[atk+'_'+dt]||1);});
            if(m>=4)weak4x.push(atk);else if(m>=2)weak2x.push(atk);
            else if(m===0)immune.push(atk);else if(m<=0.5)resist05.push(atk);
        });
        let h=`<div class="flex items-center gap-4 mb-3">
            <img src="${spr(p.name)}" data-id="${p.id}" class="w-16 h-16 sprite-hover">
            <div class="flex-1">
                <p class="font-bold text-white text-lg">${p.name_fr||p.name} <span class="text-xs text-gray-500">#${p.id} BST:${bst}</span></p>
                <div class="flex gap-1 mt-1">${pill(p.type1)}${p.type2?' '+pill(p.type2):''}</div>
                <p class="text-xs text-gray-400 mt-1">${p.attack>=p.sp_attack?'Physique (Atk:'+p.attack+')':'Special (SpA:'+p.sp_attack+')'} | Spe:${p.speed}</p>
            </div>
        </div>`;
        if(weak4x.length) h+=`<div class="mb-1"><span class="text-xs font-bold" style="color:#ff5252">x4 :</span> ${weak4x.map(t=>pill(t)).join(' ')}</div>`;
        if(weak2x.length) h+=`<div class="mb-1"><span class="text-xs font-bold" style="color:#ff8a80">x2 :</span> ${weak2x.map(t=>pill(t)).join(' ')}</div>`;
        if(immune.length) h+=`<div class="mb-1"><span class="text-xs font-bold" style="color:#40c4ff">x0 :</span> ${immune.map(t=>pill(t)).join(' ')}</div>`;
        if(resist05.length) h+=`<div class="mb-1"><span class="text-xs font-bold" style="color:#69f0ae">x0.5 :</span> ${resist05.map(t=>pill(t)).join(' ')}</div>`;
        h+=`<p class="text-[10px] mt-2 p-2 rounded" style="background:rgba(0,229,255,0.05);color:#00e5ff">
        Voici ce que l'overlay afficherait en temps reel quand l'OCR detecte cet adversaire en combat.</p>`;
        el.innerHTML=h;
    }catch(e){el.innerHTML=`<p class="text-red-400">Erreur calcul faiblesses</p>`;}
}

// === OVERLAY MODE ===
async function toggleOverlay(){
    const ov=document.getElementById('overlay-mode');
    const sidebar=document.querySelector('aside');
    const main=document.querySelector('main');
    if(ov.classList.contains('hidden')){
        // Ensure type chart is loaded for weakness calculations
        if(!window._typeChart){
            try{const d=await fetch('/api/type-chart').then(r=>r.json());window._typeChart=d.chart;}catch(e){}
        }
        ov.classList.remove('hidden');
        sidebar.classList.add('hidden');
        main.style.display='none';
        document.getElementById('ov-search').value='';
        document.getElementById('ov-search').focus();
    }else{
        ov.classList.add('hidden');
        sidebar.classList.remove('hidden');
        main.style.display='';
    }
}
document.addEventListener('keydown',e=>{
    if(e.key==='F9'){e.preventDefault();toggleOverlay();}
});
// Overlay search
(function(){
    const input=document.getElementById('ov-search');
    const result=document.getElementById('ov-result');
    if(!input)return;
    let debounce;
    input.addEventListener('input',()=>{
        clearTimeout(debounce);
        debounce=setTimeout(async()=>{
            const q=input.value.trim();
            if(q.length<2){result.innerHTML='<p class="text-gray-600 text-sm">Tape le nom du Pokemon adverse...</p>';return;}
            try{
                const pks=await fetch('/api/pokemon/search/'+encodeURIComponent(q)).then(r=>r.json());
                if(!pks.length){result.innerHTML='<p class="text-gray-500 text-sm">Aucun resultat</p>';return;}
                const p=pks[0];
                const det=await fetch('/api/pokemon/'+p.id).then(r=>r.json());
                const types=[det.type1];if(det.type2)types.push(det.type2);
                // Build weakness analysis
                const wk=await fetch('/api/type-effectiveness/'+types.join('/')).then(r=>r.json()).catch(()=>null);
                let h=`<div class="flex items-center gap-4 mb-4">
                    <img src="${spr(det.name)}" class="w-20 h-20">
                    <div>
                        <p class="text-xl font-black text-white">${det.name_fr||det.name}</p>
                        <p class="text-xs text-gray-500">#${String(det.id).padStart(3,'0')} ${det.name_fr?det.name:''}</p>
                        <div class="flex gap-1 mt-1">${pill(det.type1)}${det.type2?' '+pill(det.type2):''}</div>
                        <p class="text-xs text-gray-400 mt-1">BST ${det.hp+det.attack+det.defense+det.sp_attack+det.sp_defense+det.speed} | PV ${det.hp} | VIT ${det.speed}</p>
                    </div>
                </div>`;
                // Calculate weaknesses from type chart
                const eff={};
                const allTypes=Object.keys(TC);
                allTypes.forEach(atk=>{
                    let mult=1;
                    types.forEach(def=>{
                        const key=atk+'_'+def;
                        if(typeof window._typeChart==='object'&&window._typeChart[key]!==undefined)mult*=window._typeChart[key];
                    });
                    if(mult!==1)eff[atk]=mult;
                });
                const x4=Object.entries(eff).filter(([,v])=>v>=4).map(([t])=>t);
                const x2=Object.entries(eff).filter(([,v])=>v===2).map(([t])=>t);
                const r05=Object.entries(eff).filter(([,v])=>v===0.5).map(([t])=>t);
                const r025=Object.entries(eff).filter(([,v])=>v<=0.25&&v>0).map(([t])=>t);
                const imm=Object.entries(eff).filter(([,v])=>v===0).map(([t])=>t);
                if(x4.length)h+=`<div class="mb-2"><p class="text-xs font-bold mb-1" style="color:#ff5252">TRES FAIBLE x4</p><div class="flex flex-wrap gap-1">${x4.map(t=>pill(t)).join(' ')}</div></div>`;
                if(x2.length)h+=`<div class="mb-2"><p class="text-xs font-bold mb-1" style="color:#ff8a80">FAIBLE x2</p><div class="flex flex-wrap gap-1">${x2.map(t=>pill(t)).join(' ')}</div></div>`;
                if(imm.length)h+=`<div class="mb-2"><p class="text-xs font-bold mb-1" style="color:#40c4ff">IMMUNITE x0</p><div class="flex flex-wrap gap-1">${imm.map(t=>pill(t)).join(' ')}</div></div>`;
                if(r025.length)h+=`<div class="mb-2"><p class="text-xs font-bold mb-1" style="color:#69f0ae">RESISTE x0.25</p><div class="flex flex-wrap gap-1">${r025.map(t=>pill(t)).join(' ')}</div></div>`;
                if(r05.length)h+=`<div class="mb-2"><p class="text-xs font-bold mb-1" style="color:#b9f6ca">RESISTE x0.5</p><div class="flex flex-wrap gap-1">${r05.map(t=>pill(t)).join(' ')}</div></div>`;
                // Quick action line
                const atk=[...x4,...x2];
                if(atk.length)h+=`<div class="mt-3 p-2 rounded text-sm" style="background:rgba(255,64,129,0.1);border:1px solid rgba(255,64,129,0.2)"><span style="color:#ff4081" class="font-bold">Attaque avec :</span> <span class="text-white">${atk.map(t=>tfr(t)).join(', ')}</span></div>`;
                result.innerHTML=h;
            }catch(e){result.innerHTML='<p class="text-red-400 text-sm">Erreur</p>';}
        },200);
    });
})();

// === Real Overlay (PyQt6 OCR) ===
async function toggleRealOverlay(){
    const btn=document.getElementById('btn-overlay');
    const dot=document.getElementById('overlay-status-dot');
    const txt=document.getElementById('overlay-status-text');
    // Check current status
    const st=await fetch('/api/overlay/status').then(r=>r.json()).catch(()=>({running:false}));
    if(st.running){
        // Stop
        const r=await fetch('/api/overlay/stop',{method:'POST'}).then(r=>r.json());
        btn.textContent='Lancer Overlay OCR';btn.style.borderColor='#d500f9';btn.style.color='#d500f9';
        dot.style.background='#666';txt.textContent='Overlay inactif';
        showToast('Overlay arrete');
    }else{
        // Start
        btn.textContent='Demarrage...';btn.disabled=true;
        const r=await fetch('/api/overlay/start',{method:'POST'}).then(r=>r.json());
        btn.disabled=false;
        if(r.status==='started'||r.status==='already_running'){
            btn.textContent='Arreter Overlay';btn.style.borderColor='#ff5252';btn.style.color='#ff5252';
            dot.style.background='#69f0ae';txt.textContent='Overlay actif (F9/F10)';
            showToast('Overlay lance ! F9=toggle, F10=etendu');
        }else{
            btn.textContent='Lancer Overlay OCR';
            showToast(r.message||'Erreur overlay');
        }
    }
}
// Poll overlay status every 10s
setInterval(async()=>{
    const st=await fetch('/api/overlay/status').then(r=>r.json()).catch(()=>({running:false}));
    const dot=document.getElementById('overlay-status-dot');
    const txt=document.getElementById('overlay-status-text');
    const btn=document.getElementById('btn-overlay');
    if(st.running){
        dot.style.background='#69f0ae';txt.textContent='Overlay actif';
        btn.textContent='Arreter Overlay';btn.style.borderColor='#ff5252';btn.style.color='#ff5252';
    }else{
        dot.style.background='#666';txt.textContent='Overlay inactif';
        btn.textContent='Lancer Overlay OCR';btn.style.borderColor='#d500f9';btn.style.color='#d500f9';
    }
},10000);

// Only load visible page (dashboard) at startup — others load on navigation
loadAbilityFR();loadDash();loadChart();checkGame();dashLoadRoute();
