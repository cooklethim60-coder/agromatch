/* AgroMatch additions: a connected agriculture intelligence + community experience. */
const NAV=[
 {id:'home',title:'Overview',ico:'home',group:'PLATFORM'},
 {id:'earth',title:'Satellite Earth',ico:'earth',group:'INTELLIGENCE'},
 {id:'fields',title:'My Fields',ico:'fields',group:'INTELLIGENCE'},
 {id:'doctor',title:'Field Doctor',ico:'doctor',group:'INTELLIGENCE'},
 {id:'weather',title:'Weather & Climate',ico:'weather',group:'INTELLIGENCE'},
 {id:'rot',title:'Rotation Remix',ico:'rot',group:'INTELLIGENCE'},
 {id:'co',title:'Farm Copilot',ico:'co',group:'INTELLIGENCE'},
 {id:'match',title:'Farm Match',ico:'disc',group:'COMMUNITY'},
 {id:'chat',title:'Farm Chat',ico:'chat',group:'COMMUNITY'},
 {id:'feed',title:'Farm Feed',ico:'feed',group:'COMMUNITY'},
 {id:'music',title:'Farm Symphony',ico:'music',group:'EXPLORE'},
 {id:'knowledge',title:'Knowledge Hub',ico:'knowledge',group:'EXPLORE'},
 {id:'reports',title:'Reports',ico:'reports',group:'EXPLORE'}];
const moreTabs=['doctor','weather','rot','co','chat','music','knowledge','reports'];
// Shared RU/EN navigation for Kazakhstan and international users.
// Detailed feature content retains source-specific English text until fully translated.
const NAV_RU={home:'Обзор',earth:'Карта и спутники',fields:'Мои поля',doctor:'Проверка поля',
 weather:'Погода и климат',rot:'Севооборот',co:'AI-агроном',match:'Фермеры',
 chat:'Сообщения',feed:'Сообщество',music:'Музыка полей',knowledge:'База знаний',
 reports:'Отчёты',more:'Ещё'};
function uiLanguage(){return localStorage.agromatchLanguage==='en'?'en':'ru'}
function navLabel(x){return uiLanguage()==='ru'?(NAV_RU[x.id]||x.title):x.title}
function toggleUiLanguage(){localStorage.agromatchLanguage=uiLanguage()==='ru'?'en':'ru';if(typeof closeOv==='function')closeOv();draw()}

const featureIcons={fields:'<path d="M3 3h18v18H3zM3 11h18M11 3v18"/>',doctor:'<path d="M12 3v18M3 12h18M5 5l14 14"/>',weather:'<path d="M4 17a5 5 0 0 1 4-8 7 7 0 0 1 13 4 4 4 0 0 1-4 7H8z"/>',chat:'<path d="M4 4h16v12H9l-5 4z"/>',feed:'<path d="M5 5h14M5 11h14M5 17h10"/>',music:'<path d="M9 18V5l12-2v13M9 8l12-2"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',knowledge:'<path d="M3 5c3-2 6-2 9 0 3-2 6-2 9 0v15c-3-2-6-2-9 0-3-2-6-2-9 0zM12 5v15"/>',reports:'<path d="M6 3h9l4 4v14H6zM9 12h7M9 16h7"/>',more:'<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>'};
function shellNav(){
 const groups=['PLATFORM','INTELLIGENCE','COMMUNITY','EXPLORE'];
 const desktop=`<div class="nav-brand"><div class="brand-mark">A</div><div><b>AGROMATCH</b><small>EARTH INTELLIGENCE</small></div></div>`+
  groups.map(g=>`<div class="nav-group"><div class="nav-label">${g}</div>${NAV.filter(x=>x.group===g).map(x=>`<button class="nav-entry ${S.tab===x.id?'on':''}" onclick="tab('${x.id}')">${ic(x.ico)}<span>${navLabel(x)}</span>${x.id==='chat'&&S.notif?`<i class="nav-count">${S.notif}</i>`:''}</button>`).join('')}</div>`).join('')+
  `<div class="nav-footer"><span class="status-led"></span> NASA • Earth data intelligence <button class="language-switch" onclick="toggleUiLanguage()" title="Русский / English">${uiLanguage()==='ru'?'English':'Русский'}</button></div>`;
 const mobile=[...NAV.filter(x=>['home','earth','fields','feed','match'].includes(x.id)),{id:'more',title:'More',ico:'more'}];
 return `<nav class="desktop-nav">${desktop}</nav><nav class="mobile-nav">${mobile.map(x=>`<button class="${S.tab===x.id||(x.id==='more'&&moreTabs.includes(S.tab))?'on':''}" onclick="${x.id==='more'?'openMore()':`tab('${x.id}')`}">${ic(x.ico)}<span>${uiLanguage()==='ru'?navLabel(x):(x.title==='Satellite Earth'?'Earth':x.title==='Overview'?'Home':x.title==='My Fields'?'Fields':x.title==='Farm Feed'?'Feed':x.title==='Farm Match'?'Match':x.title)}</span></button>`).join('')}</nav>`;
}
function openMore(){ovOpen(`<h1>Explore AgroMatch</h1><p class="mut">Choose a workspace</p><div class="extra-menu">${NAV.map(x=>`<button onclick="closeOv();tab('${x.id}')">${ic(x.ico)}<span>${navLabel(x)}</span></button>`).join('')}</div><button class="btn o s language-mobile" onclick="toggleUiLanguage()">🌐 ${uiLanguage()==='ru'?'English':'Русский'}</button>`)}
function selFieldHtml(action){return `<label>Selected field</label><select onchange="S.extraField=+this.value;${action}()">${S.me.fields.map(f=>`<option value="${f.id}" ${f.id===S.extraField?'selected':''}>${esc(f.name)} · ${f.area_ha} ha</option>`).join('')}</select>`}
function ensureField(){if(!S.extraField||!S.me.fields.some(f=>f.id===S.extraField))S.extraField=S.me.fields[0]?.id||null;return S.extraField}

function fieldsFiltered(){
 let fields=[...(S.me?.fields||[])],query=String(S.fieldQuery||'').trim().toLowerCase();
 if(query)fields=fields.filter(f=>(f.name+' '+(f.soil||'')+' '+(f.crops||[]).join(' ')).toLowerCase().includes(query));
 switch(S.fieldSort){
  case 'area-desc':fields.sort((a,b)=>(Number(b.area_ha)||0)-(Number(a.area_ha)||0));break;
  case 'area-asc':fields.sort((a,b)=>(Number(a.area_ha)||0)-(Number(b.area_ha)||0));break;
  default:fields.sort((a,b)=>String(a.name).localeCompare(String(b.name)));break;
 }
 return fields;
}
function fieldsListMarkup(){
 const ru=uiLanguage()==='ru',t=(a,b)=>ru?a:b,filtered=fieldsFiltered();
 if(!filtered.length)return `<div class="fields-empty"><span aria-hidden="true">⌕</span><h3>${t('Поля не найдены','No matching fields')}</h3><p class="mut">${t('Попробуйте изменить запрос или сбросить поиск.','Try a different search or clear the filter.')}</p><button class="btn o s" onclick="S.fieldQuery='';const x=$('#fieldSearch');if(x)x.value='';renderFieldsList()">${t('Сбросить','Clear search')}</button></div>`;
 return filtered.map(f=>{
  const s=f.snapshots?.[0],m=s?.metrics||{};
  return `<article class="field-tile field-management-card">
   <div class="field-management-header"><span class="field-management-id">FIELD ${f.id}</span>${m.simulated?tag('s'):m.source?tag('n'):'<span class="mini-source">NO DATA</span>'}</div>
   <h2>${esc(f.name)}</h2><p class="mut">${esc(f.soil||t('Почва не указана','Soil not specified'))} · ${Number(f.area_ha||0).toLocaleString(ru?'ru-RU':'en-US')} ha</p>
   <div class="field-management-kpis"><div><small>${t('Осадки / период','Rain / period')}</small><strong>${m.rain_mm==null?'—':esc(m.rain_mm)+' mm'}</strong></div><div><small>${t('Средняя температура','Mean temperature')}</small><strong>${m.temp_c==null?'—':esc(m.temp_c)+' °C'}</strong></div></div>
   <div class="field-management-footer"><button class="btn s" onclick="ovField(${f.id})">${t('Подробности','Details')} ↗</button><button class="btn o s" onclick="focusEarthField(${f.id})">${t('На карте','Map')} ⌖</button><button class="btn o s" onclick="S.extraField=${f.id};tab('doctor')">${t('Анализ','Analysis')}</button></div>
  </article>`;
 }).join('');
}
function renderFieldsList(){
 const e=$('#fieldsResults');if(e)e.innerHTML=fieldsListMarkup();
 const count=$('#fieldsVisibleCount');if(count)count.textContent=fieldsFiltered().length;
}
function fieldsComparisonHTML(){
 const fields=S.me?.fields||[],ru=uiLanguage()==='ru',t=(a,b)=>ru?a:b;
 if(fields.length<2)return `<p class="mut">${t('Добавьте второе поле, чтобы сравнить показатели.','Add a second field to compare indicators.')}</p>`;
 const ids=fields.map(x=>x.id);if(!ids.includes(S.compareA))S.compareA=ids[0];
 if(!ids.includes(S.compareB)||S.compareB===S.compareA)S.compareB=ids.find(x=>x!==S.compareA)||ids[1];
 const a=fields.find(x=>x.id===S.compareA),b=fields.find(x=>x.id===S.compareB);
 const opts=which=>fields.map(f=>`<option value="${f.id}" ${f.id===which?'selected':''}>${esc(f.name)}</option>`).join('');
 const val=(m,k,unit='')=>m?.[k]==null?'—':esc(m[k])+unit;
 const rows=[
  [t('Площадь','Area'),(f,m)=>Number(f.area_ha||0).toLocaleString(ru?'ru-RU':'en-US')+' ha'],
  [t('Осадки / период','Period rainfall'),(f,m)=>val(m,'rain_mm',' mm')],
  [t('Средняя температура','Mean temperature'),(f,m)=>val(m,'temp_c',' °C')],
  [t('Модельная влажность (0–1)','Modeled wetness (0–1)'),(f,m)=>val(m,'wetness')],
  [t('Тип почвы','Soil type'),f=>esc(f.soil||'—')],
  [t('Последние данные','Last available data'),(f,m)=>esc(m?.last_obs||'—')]
 ];
 const ma=a.snapshots?.[0]?.metrics,mb=b.snapshots?.[0]?.metrics;
 const source=m=>m?.simulated?tag('s'):m?.source?tag('n'):'<span class="source-unknown">NO DATA</span>';
 return `<div class="field-compare-inputs"><label>${t('Поле A','Field A')}<select aria-label="${t('Первое поле','First field')}" onchange="S.compareA=+this.value;renderFieldComparison()">${opts(a.id)}</select></label><label>${t('Поле B','Field B')}<select aria-label="${t('Второе поле','Second field')}" onchange="S.compareB=+this.value;renderFieldComparison()">${opts(b.id)}</select></label></div>
 <div class="field-compare-scroll"><table class="field-compare-table"><thead><tr><th>${t('Показатель','Indicator')}</th><th>${esc(a.name)}<div>${source(ma)}</div></th><th>${esc(b.name)}<div>${source(mb)}</div></th></tr></thead><tbody>${rows.map(([name,calc])=>`<tr><th>${name}</th><td>${calc(a,ma)}</td><td>${calc(b,mb)}</td></tr>`).join('')}</tbody></table></div>
 <p class="footnote">${t('Это сравнение не является оценкой урожайности. Периоды данных могут различаться; NASA POWER отражает региональную сетку, а SIMULATED — демонстрационные значения.','Not a yield forecast. Observation periods may differ; NASA POWER is regional grid data and SIMULATED values are demonstrations.')}</p>`;
}
function renderFieldComparison(){const e=$('#fieldComparisonResults');if(e)e.innerHTML=fieldsComparisonHTML()}
function myFields(){
 const ru=uiLanguage()==='ru',t=(a,b)=>ru?a:b,fields=S.me.fields||[];
 return hdr(t('Мои поля','My fields'),t('Контуры, климат, культура и история участков','Boundaries, climate, crops and field histories'))+
 `<div class="fields-management">
 <div class="fields-management-hero"><div><div class="section-eyebrow">${t('ЗЕМЕЛЬНЫЙ БАНК','FIELD PORTFOLIO')}</div><h2>${fields.length} ${t('полей в хозяйстве','fields in your portfolio')}</h2><p>${t('Найдите нужный участок или перейдите к его координатам на карте.','Find any parcel, explore its history or jump to its map location.')}</p></div><div class="fields-management-actions"><button class="btn s" onclick="S.scr='fieldEd';S.edit=null;S.pts=[];draw()">+ ${t('Новое поле','Add field')}</button><button class="btn o s" onclick="downloadFieldsGeoJSON()">↓ GeoJSON</button></div></div>
 <div class="fields-management-toolbar"><label for="fieldSearch">${t('Поиск по названию, почве, культуре','Search fields by name, soil or crop')}<input id="fieldSearch" type="search" placeholder="${t('Например: пшеница','e.g. wheat')}" value="${esc(S.fieldQuery||'')}" oninput="S.fieldQuery=this.value;renderFieldsList()"></label><label for="fieldSort">${t('Сортировка','Sort fields')}<select id="fieldSort" onchange="S.fieldSort=this.value;renderFieldsList()"><option value="name" ${S.fieldSort==='name'||!S.fieldSort?'selected':''}>${t('По названию','Name')}</option><option value="area-desc" ${S.fieldSort==='area-desc'?'selected':''}>${t('Площадь ↓','Area ↓')}</option><option value="area-asc" ${S.fieldSort==='area-asc'?'selected':''}>${t('Площадь ↑','Area ↑')}</option></select></label><span class="fields-result-count"><b id="fieldsVisibleCount">${fieldsFiltered().length}</b> / ${fields.length}</span></div>
 <details class="field-comparison"><summary><span>◫</span> ${t('Сравнить два поля','Compare two fields')} <small>${t('Региональные условия и история','Regional conditions and history')}</small></summary><div id="fieldComparisonResults">${fieldsComparisonHTML()}</div></details>
 <div class="fields-result-grid" id="fieldsResults">${fieldsListMarkup()}</div>
 <p class="footnote">${t('Климатические показатели NASA POWER имеют региональное разрешение. Данные с пометкой SIMULATED не являются наблюдениями.','NASA POWER climate estimates are regional; SIMULATED values are not observations.')}</p>
 </div>`;
}
function doctorPage(){ensureField();return hdr('Field Doctor','Evidence first · transparent diagnostics')+`<div class="feature-panel">${selFieldHtml('loadDoctor')}<div id="doctorResults" class="loading-region">Checking available observations…</div></div><div class="footnote">Not a medical-style diagnosis for crops. Rule-based indicators highlight potential problems; confirm them with field inspections.</div>`}
async function loadDoctor(){if(!$('#doctorResults'))return;$('#doctorResults').innerHTML='<p class="mut">Analysing available data…</p>';await tryit(async()=>{const r=await api(`/fields/${S.extraField}/doctor`);if(!$('#doctorResults'))return;$('#doctorResults').innerHTML=`<div class="row sb"><h2>Field observations</h2><span class="tag f_">RULE-BASED</span></div>${r.findings.map(v=>`<div class="finding ${v.level}"><div class="row sb"><b>${esc(v.title)}</b><span class="mini-source">${esc(v.source)}</span></div><p><b>Evidence:</b> ${esc(v.evidence)}</p><p>${esc(v.interpretation)}</p><div class="recommend"><b>Recommended check:</b> ${esc(v.action)}</div></div>`).join('')}<p class="mut">${esc(r.limitations)}</p><div class="row"><button class="btn s" onclick="loadAiDoctor()">Generate AI interpretation</button><button class="btn o s" onclick="S.cop.field=S.extraField;S.cop.mode='do';tab('co')">Farm Copilot</button></div><div id="aiDoctorResult"></div>`})}
async function loadAiDoctor(){const el=$('#aiDoctorResult');if(!el)return;el.innerHTML='<p class="mut">Asking the configured AI provider…</p>';
 try{const r=await api(`/fields/${S.extraField}/doctor/ai`,{b:{}});
  if($('#aiDoctorResult'))$('#aiDoctorResult').innerHTML=`<div class="feature-panel"><span class="tag a_">AI INTERPRETATION</span><p class="mut">${esc(r.provider)} · Not a field measurement or diagnosis</p><div class="md">${md(r.text)}</div></div>`;
 }catch(e){if($('#aiDoctorResult'))$('#aiDoctorResult').innerHTML=`<div class="warn">${esc(e.message)}. Configure Gemini / Grok keys on the backend.</div>`}}
function weatherPage(){
 ensureField();
 return hdr('Weather & Climate','Погода на поле · прогноз с числами и таблицей')+
 `<div class="feature-panel weather-dashboard">
 <div class="weather-toolbar">${selFieldHtml('loadWeather')}
 <button class="btn o s" onclick="loadWeather(true)" title="Запросить свежий прогноз">↻ Обновить прогноз</button></div>
 <div id="weatherResults" class="loading-region" aria-live="polite">Загружаем прогноз погоды…</div></div>`;
}
function weatherNum(x,digits=0,suffix=''){
 const n=Number(x);return x==null||!Number.isFinite(n)?'—':n.toLocaleString('ru-RU',{maximumFractionDigits:digits,minimumFractionDigits:digits})+suffix;
}
function weatherIcon(code){
 const c=Number(code);
 return c===0?'☀️':c>=1&&c<=3?'⛅':c>=45&&c<=48?'🌫️':c>=51&&c<=67?'🌧️':c>=71&&c<=77?'❄️':c>=80&&c<=82?'🌦️':c>=95?'⛈️':'🌤️';
}
function weatherDate(d){const date=new Date(d+'T12:00:00');return Number.isNaN(date.getTime())?esc(d):date.toLocaleDateString('ru-RU',{weekday:'short',day:'numeric',month:'short'});}
function renderWeatherDashboard(){
 const w=S.weatherData,el=$('#weatherResults');
 if(!w||!el)return;
 const days=w.days.slice(0,S.weatherRange===3?3:7);
 const f=S.me.fields.find(z=>z.id===S.extraField);
 const m=f?.snapshots?.[0]?.metrics;
 const sum=k=>days.every(d=>d[k]!=null&&Number.isFinite(Number(d[k])))?days.reduce((a,d)=>a+Number(d[k]),0):null;
 const validHigh=days.filter(d=>d.high!=null).map(d=>Number(d.high));
 const high=validHigh.length?Math.max(...validHigh):null;
 const lows=days.filter(d=>d.low!=null).map(d=>Number(d.low));
 const low=lows.length?Math.min(...lows):null;
 const chance=days.filter(d=>d.rain_chance!=null).map(d=>Number(d.rain_chance));
 const chanceMax=chance.length?Math.max(...chance):null;
 const card=(symbol,title,value,note)=>`<div class="weather-kpi"><span class="weather-kpi-label">${symbol} ${title}</span><strong>${value}</strong><small>${note}</small></div>`;
 el.innerHTML=`<div class="row sb weather-head"><div><div class="section-eyebrow">OPEN-METEO · ПРОГНОЗ</div><h2>${esc(f?.name||'Поле')}</h2><p class="mut">По координатам поля · ${esc(w.timezone||'часовой пояс модели')}</p></div><span class="tag f_">FORECAST</span></div>
 <p class="weather-source-hint">📍 Точки представляют расчётные ячейки погодной модели, а не локальные датчики на ферме. Полный прогноз: ${w.complete_days??"—"} из ${w.days.length} дней.</p><div class="weather-filters" role="group" aria-label="Период прогноза"><span>Показать:</span><button class="chip ${S.weatherRange===3?'on':''}" onclick="S.weatherRange=3;renderWeatherDashboard()">3 дня</button><button class="chip ${S.weatherRange!==3?'on':''}" onclick="S.weatherRange=7;renderWeatherDashboard()">7 дней</button></div>
 <div class="weather-kpis">
 ${card('🌡️','Макс. температура',weatherNum(high,1,' °C'),'За выбранный период')}
 ${card('❄️','Мин. температура',weatherNum(low,1,' °C'),'За выбранный период')}
 ${card('🌧️','Всего осадков',weatherNum(sum('rain'),1,' мм'),'Сумма за '+days.length+' дн.')}
 ${card('☔','Вероятность дождя',weatherNum(chanceMax,0,' %'),'Максимум за период')}
 ${card('💧','Влажность воздуха',weatherNum(w.humidity_today,0,' %'),'Прогноз на сегодня')}
 ${card('💨','Ветер',weatherNum(w.wind_today,1,' км/ч'),'Макс. за сегодня')}
 </div>
 <h2>Прогноз по дням</h2><div class="weather-week">${days.map(d=>`<div class="weather-day"><small>${weatherDate(d.date)}</small><div class="weather-symbol">${weatherIcon(d.code)}</div><strong>${weatherNum(d.high,0,'°')}</strong><span>мин. ${weatherNum(d.low,0,'°')}</span><b>${weatherNum(d.rain,1,' мм')}</b><small>☔ ${weatherNum(d.rain_chance,0,'%')}</small></div>`).join('')}</div>
 <div class="row sb"><h2>Таблица погодных условий</h2><span class="mut">Обновляется при выборе поля</span></div>
 <div class="weather-table-wrap"><table class="weather-data-table"><thead><tr><th>Дата</th><th>Условия</th><th>Макс., °C</th><th>Мин., °C</th><th>Осадки, мм</th><th>Вероятность, %</th></tr></thead><tbody>${days.map(d=>`<tr><td>${weatherDate(d.date)}</td><td class="weather-symbol-sm">${weatherIcon(d.code)}</td><td>${weatherNum(d.high,1)}</td><td>${weatherNum(d.low,1)}</td><td>${weatherNum(d.rain,1)}</td><td>${weatherNum(d.rain_chance)}</td></tr>`).join('')}</tbody></table></div>
 <h2>Осадки по дням (мм)</h2>${bars(days.map(d=>Number(d.rain)||0),days.map(d=>d.date.slice(8)))}
 <h2>Предупреждения</h2>${w.warnings?.length?w.warnings.filter(z=>!z.date||days.some(d=>d.date===z.date)).map(z=>`<div class="finding warning"><b>${esc(z.kind)}</b> ${z.date?'· '+weatherDate(z.date):''}<p>${esc(z.text)}</p></div>`).join(''):'<p class="mut">По заданным порогам предупреждений нет. Это не гарантия отсутствия риска.</p>'}
 <h2>NASA POWER · климатическая история</h2>${m?`<div class="weather-kpis weather-history">
 ${card('🌧️','Осадки за год',weatherNum(m.rain_mm,0,' мм'),'Исторический региональный показатель')}
 ${card('🌡️','Средняя температура',weatherNum(m.temp_c,1,' °C'),'Исторический региональный показатель')}
 ${card('🌱','Влажность почвы',weatherNum(m.wetness,3),'Модельная, без единиц измерения')}
 </div>${(m.monthly||[]).length>1?line((m.monthly||[]).slice(-12).map(a=>a.temp),(m.monthly||[]).slice(-12).map(a=>a.m.slice(5)),'var(--pri)'):''}
 <p class="mut">Источник: ${esc(m.source||'не указан')} ${m.simulated?tag('s'):tag('n')}</p>`:'<p class="mut">Нет исторических измерений для этого поля.</p>'}
 <div class="footnote">Прогноз: ${esc(w.source)} · получен ${new Date(w.fetched_at*1000).toLocaleString('ru-RU')} · ${esc(w.limitations)}. Погодные прогнозы не являются измерениями датчиков на поле.</div>`;
}
async function loadWeather(refresh=false){
 const el=$('#weatherResults');if(!el)return;
 const fid=S.extraField;
 S.weatherData=null;
 el.innerHTML='<p class="mut">Получаем свежий прогноз погоды…</p>';
 try{
  const w=await api(`/fields/${fid}/weather${refresh?'?refresh=true':''}`);
  if(S.extraField!==fid||!$('#weatherResults'))return;
  S.weatherData=w;
  S.weatherRange=S.weatherRange===3?3:7;
  renderWeatherDashboard();
 }catch(e){
  if($('#weatherResults')&&S.extraField===fid)$('#weatherResults').innerHTML=`<div class="warn">Не удалось загрузить прогноз: ${esc(e.message)}. Проверь подключение к Open-Meteo и попробуй обновить данные.</div>`;
 }
}
function feedPage(){return hdr('Farm Feed','From the fields, to the community')+`<div class="feature-panel"><div class="section-eyebrow">SHARE AN UPDATE</div><textarea id="newpost" maxlength="2000" rows="3" placeholder="A field observation, crop-rotation idea, or a practical question…"></textarea><div class="row sb"><span class="mut">Visible to AgroMatch members</span><button class="btn s" onclick="publishPost()">Publish</button></div></div><div id="feedResults" class="loading-region">Loading community posts…</div>`}
async function loadFeed(){const el=$('#feedResults');if(!el)return;el.innerHTML='<p class="mut">Loading posts…</p>';try{const items=await api('/feed');S.feed=items;renderFeed()}catch(e){el.innerHTML=`<div class="warn">${esc(e.message)}</div>`}}
function renderFeed(){const el=$('#feedResults');if(!el)return;el.innerHTML=(S.feed||[]).length?(S.feed||[]).map(p=>`<article class="social-post"><div class="row sb"><div><b>${esc(p.author)}</b><div class="mut">${esc(p.region)} · ${when(p.created)}</div></div><span class="tag f_">FARMER</span></div><p>${esc(p.body).replace(/\n/g,'<br>')}</p><div class="post-actions"><button class="chip ${p.liked?'on':''}" onclick="likePost(${p.id})">${p.liked?'♥':'♡'} ${p.likes} likes</button><span class="mut">${p.comments.length} comments</span></div>${p.comments.map(c=>`<div class="post-comment"><b>${esc(c.author)}</b> ${esc(c.body)}<small>${when(c.created)}</small></div>`).join('')}<div class="row"><input id="comment-${p.id}" maxlength="1000" placeholder="Comment on this update" onkeydown="if(event.key==='Enter')addComment(${p.id})"><button class="btn s" onclick="addComment(${p.id})">Reply</button></div></article>`).join(''):'<div class="feature-panel"><h2>No posts yet</h2><p class="mut">Start the conversation with a field observation or useful farming tip.</p></div>'}
async function publishPost(){await tryit(async()=>{const text=$('#newpost').value.trim();if(!text)return;await api('/feed',{b:{body:text}});$('#newpost').value='';await loadFeed();toast('Post published')})}
async function likePost(id){await tryit(async()=>{await api(`/feed/${id}/like`,{b:{}});await loadFeed()})}
async function addComment(id){await tryit(async()=>{const val=$('#comment-'+id)?.value.trim();if(!val)return;await api(`/feed/${id}/comments`,{b:{body:val}});await loadFeed()})}
function knowledgePage(){return hdr('Knowledge Hub','Agricultural concepts made practical')+`<div class="feature-panel"><div class="row"><input id="ksearch" placeholder="Search soil, rotation, NDVI…" onkeydown="if(event.key==='Enter')loadKnowledge()"><button class="btn s" onclick="loadKnowledge()">Search</button></div><select id="kcategory" onchange="loadKnowledge()"><option value="">All topics</option>${['Satellite intelligence','Crop rotation','Soil health','Soil & water','Climate resilience','Sustainable agriculture'].map(x=>`<option>${x}</option>`).join('')}</select></div><div id="knowledgeResults" class="knowledge-grid loading-region">Loading guides…</div>`}
async function loadKnowledge(){const el=$('#knowledgeResults');if(!el)return;try{const results=await api('/knowledge?q='+encodeURIComponent($('#ksearch')?.value||'')+'&category='+encodeURIComponent($('#kcategory')?.value||''));if(!$('#knowledgeResults'))return;el.innerHTML=results.length?results.map(a=>`<button class="knowledge-tile" onclick="openArticle('${a.id}')"><span class="section-eyebrow">${esc(a.category).toUpperCase()}</span><b>${esc(a.title)}</b><span class="mut">${a.reading_minutes} min read · Field guide</span><span class="read-more">Read article →</span></button>`).join(''):'<p class="mut">No guides match that search.</p>'}catch(e){el.innerHTML=`<p class="warn">${esc(e.message)}</p>`}}
async function openArticle(id){await tryit(async()=>{const a=await api('/knowledge/'+id);ovOpen(`<div class="section-eyebrow">${esc(a.category).toUpperCase()}</div><h1 class="article-title">${esc(a.title)}</h1><p class="mut">AgroMatch knowledge guide</p><div class="article-body">${esc(a.body)}</div><div class="footnote">General education only. Check local agronomic guidance and observations.</div><button class="btn o s language-mobile" onclick="toggleUiLanguage()">🌐 ${uiLanguage()==='ru'?'English':'Русский'}</button>`)})}
function reportsPage(){return hdr('Reports','Clear field evidence, ready to share')+`<div class="feature-panel"><div class="section-eyebrow">FIELD INTELLIGENCE REPORTS</div><h2>Export observations and recommendations</h2><p class="mut">Reports contain farmer data, NASA POWER history, AppEEARS observations if available, and rule-based inspection flags. No measurements are fabricated.</p></div>${S.me.fields.map(f=>`<div class="field-tile"><div class="row sb"><b>${esc(f.name)}</b><span class="mut">${f.area_ha} ha</span></div><p class="mut">Print a report or export the underlying observations.</p><div class="row"><button class="btn s" onclick="openReport(${f.id})">Print / save PDF</button><button class="btn o s" onclick="exportReport(${f.id})">Export CSV</button></div></div>`).join('')}`}
async function reportFetch(fid,ext){const response=await fetch(`/api/reports/fields/${fid}.${ext}`,{headers:{Authorization:'Bearer '+T}});if(!response.ok)throw new Error('Report unavailable ('+response.status+')');return response}
function openReport(fid){const w=window.open('','_blank');if(!w){toast('Allow pop-ups to print reports');return}w.document.write('<title>Loading report…</title><p>Preparing field report…</p>');(async()=>{try{const r=await reportFetch(fid,'html');const text=await r.text();w.document.open();w.document.write(text);w.document.close()}catch(e){w.document.body.textContent=e.message}})()}
async function exportReport(fid){await tryit(async()=>{const r=await reportFetch(fid,'csv'),blob=await r.blob(),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`agromatch-field-${fid}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),15000)})}
function farmSymphonyPage(){ensureField();const mine=S.me.farm;S.known[mine.id]={id:mine.id,name:mine.name,region:mine.region};return hdr('Farm Symphony','Hear the patterns inside environmental data')+`<div class="feature-panel symphony-hero"><div class="section-eyebrow">ENVIRONMENTAL SONIFICATION</div><h2>Every field has a sound.</h2><p>Precipitation rhythms. Moisture textures. Temperature pitch. Translate the environment into an original procedural composition.</p><button class="btn" onclick="listen(${mine.id}).then(t=>t&&ovTrack(t))">▶ Listen to my farm</button><p class="mut">Creative mapping of available data, not a scientific measurement. Simulated inputs are labelled.</p></div><div class="feature-panel"><div class="section-eyebrow">MAKE YOUR OWN FIELD SOUND</div><h2>Choose what the music represents</h2>${selFieldHtml('loadSymphonyContext')}<div id="symphonyContext"></div><div class="option-grid">${[['rainfall','Rainfall rhythm'],['temperature','Temperature pitch'],['moisture','Soil-moisture texture'],['seasonal_change','Seasonal progression']].map(a=>`<label class="sym-option"><input type="checkbox" class="sym-opt" value="${a[0]}" checked><span>${a[1]}</span></label>`).join('')}</div><button class="btn" onclick="generateFieldSymphony()">Generate composition</button><p class="mut">Unselected properties use neutral musical settings, not fake observations.</p></div>`+musicV()}
async function generateFieldSymphony(){await tryit(async()=>{const indicators=[...document.querySelectorAll('.sym-opt:checked')].map(e=>e.value);if(!indicators.length)throw new Error('Select at least one indicator');toast('Generating sound from selected signals…');const track=await api(`/fields/${S.extraField}/symphony`,{b:{indicators}});play(track);ovTrack(track)})}
function loadSymphonyContext(){const f=S.me.fields.find(x=>x.id===S.extraField),el=$('#symphonyContext');if(!el||!f)return;const m=f.snapshots[0]?.metrics;el.innerHTML=`<p class="mut">${esc(f.name)} · ${m?.simulated?tag('s'):tag('n')} ${esc(m?.source||'No environmental data')}</p>`}

function matchPage(){return hdr('Farm Match','Discover growers with related conditions')+`<div class="row" style="margin-bottom:12px"><button class="chip" onclick="tab('chat')">My conversations (${S.matches.length})</button><button class="chip" onclick="S.disc=[];load().then(draw)">Refresh discovery</button></div>`+swipeV()}
function chatPage(){return hdr('Farm Chat','Private conversations with mutual matches')+`<div class="feature-panel"><b>Your connections</b><div class="mut">Only farmers who liked each other can start a conversation.</div></div>`+msgV()}
function satellitePanel(){ensureField();return `<div class="feature-panel satellite-lab"><div class="row sb"><div><div class="section-eyebrow">NASA APPEEARS · POINT EXTRACTION</div><h2>Measured satellite indicators</h2></div><span class="tag n">NASA</span></div>${selFieldHtml('loadEarthIntelligence();loadSatellite')}<div id="earthIntelligenceResults" class="loading-region">Checking NASA climate records…</div><div id="satelliteResults" class="loading-region">Checking observation availability…</div></div>`}
async function loadSatellite(){const el=$('#satelliteResults');if(!el)return;const fieldId=S.extraField;el.innerHTML='<p class="mut">Checking observation availability…</p>';try{const r=await api(`/fields/${fieldId}/satellite`);if(S.extraField!==fieldId||!$('#satelliteResults'))return;const obs=r.observations||[],ndvi=obs.filter(o=>o.indicator==='NDVI').sort((a,b)=>a.observed_at.localeCompare(b.observed_at));el.innerHTML=`<div class="row sb"><b>${obs.length} extracted data points</b><button class="btn s" onclick="submitSatellite()">Request NASA data</button></div><div class="row" style="margin-top:8px"><select id="nasaProduct" onchange="loadNasaLayers()"><option value="">MODIS NDVI (default)</option><option value="SPL4SMGP.007">SMAP root-zone moisture (catalog check)</option><option value="ECO_L2T_LSTE.002">ECOSTRESS temperature (catalog check)</option></select><select id="nasaLayer"><option value="">Select a verified NASA layer</option></select></div><div id="nasaCatalogInfo" class="mut">Optional: choose an additional verified NASA collection and layer before requesting extraction.</div><div class="footnote">${esc(r.limitations)} NASA Earthdata login and product access required.</div>${r.tasks.map(t=>`<div class="sat-task"><div class="row sb"><b>${esc(t.status)}</b><button class="btn o s" onclick="refreshSatellite(${t.id})">Check status</button></div><div class="mut">Task ${esc(t.remote_id)} · ${new Date(t.created*1000).toLocaleDateString()}</div>${t.error?`<div class="warn">Previous check failed: ${esc(t.error)}</div>`:''}</div>`).join('')}${obs.length?`<h3>Observed series</h3>${ndvi.length>=2?`<p class="mut">MODIS NDVI point trend (${ndvi.length} dates; QA not independently validated)</p>${line(ndvi.map(n=>n.value),ndvi.map(n=>n.observed_at.slice(5)))}`:''}${obs.slice(0,18).map(o=>`<div class="obs-row"><span>${esc(o.observed_at)} · ${esc(o.indicator)}</span><b>${o.value}</b><small>${esc(o.product)}</small></div>`).join('')}<p class="mut">Raw units and quality checks require scientific validation before comparisons.</p>`:'<p class="mut">No extracted numeric NASA observations. Map layers are visual imagery, not numerical measurements.</p>'}`;
}catch(e){if(S.extraField===fieldId&&$('#satelliteResults'))el.innerHTML=`<div class="warn">${esc(e.message)}</div>`}}
async function submitSatellite(){await tryit(async()=>{const product=$('#nasaProduct')?.value,layer=$('#nasaLayer')?.value;if(product&&!layer)throw new Error('Select a verified layer first');const x=await api(`/fields/${S.extraField}/satellite/tasks`,{b:product?{product,layer}:{}});toast('NASA extraction task submitted');await loadSatellite()})}
async function refreshSatellite(id){await tryit(async()=>{const x=await api(`/fields/${S.extraField}/satellite/tasks/${id}/refresh`,{b:{}});toast('NASA task: '+x.status);await loadSatellite()})}
async function loadHomePreview(){
 const fid=S.me.fields[0]?.id;if(!fid)return;
 const ru=uiLanguage()==='ru',t=(a,b)=>ru?a:b;
 try{
  const w=await api(`/fields/${fid}/weather`),days=w.days||[],today=days[0]||{};
  if($('#homeForecast')){
   const rain=days.length&&days.every(d=>d.rain!=null)?weatherNum(days.reduce((a,d)=>a+Number(d.rain),0),1,' mm'):'—';
   const outlook=w.warnings?.length?t('Проверьте погодные риски в полном прогнозе.','Review weather risks in the full forecast.'):t('Пороговые предупреждения не обнаружены.','No threshold alerts reported.');
   $('#homeForecast').innerHTML=`<div class="home-weather-summary"><div class="home-weather-current"><span class="weather-symbol">${weatherIcon(today.code)}</span><strong>${weatherNum(today.high,0,' °C')}</strong><small>${t('Дневной максимум','Daytime high')}</small></div><div class="home-weather-metrics"><span>${t('Осадки за 7 дней','7-day rainfall')}<b>${rain}</b></span><span>${t('Мин. сегодня','Low today')}<b>${weatherNum(today.low,0,' °C')}</b></span></div></div><p class="home-weather-note">${outlook}</p><p class="home-weather-source">OPEN-METEO · ${t('Прогноз модели','Model forecast')} · ${esc(w.timezone||'UTC')}</p>`;
  }
 }catch(e){if($('#homeForecast'))$('#homeForecast').innerHTML='<p class="mut">'+t('Прогноз временно недоступен. Попробуйте позже.','Forecast currently unavailable. Try again later.')+'</p>'}
 try{
  const feed=await api('/feed?limit=3');
  if($('#homeFeed'))$('#homeFeed').innerHTML=feed.length?feed.map(p=>{
   const author=String(p.author||t('Фермер','Farmer'));
   return `<div class="command-feed-item"><span class="command-feed-avatar">${esc(author[0]?.toUpperCase()||'F')}</span><div><b>${esc(author)}</b><p>${esc(String(p.body||'').slice(0,110))}</p></div></div>`;
  }).join(''):'<p class="mut">'+t('Публикаций пока нет. Начните обсуждение в сообществе.','No updates yet. Start a conversation in the community.')+'</p>';
 }catch(e){if($('#homeFeed'))$('#homeFeed').textContent=t('Сообщество временно недоступно.','Community currently unavailable.')}
}
function extraAfter(){if(S.scr!=='app')return;({home:loadHomePreview,doctor:loadDoctor,weather:loadWeather,feed:loadFeed,knowledge:loadKnowledge,earth:()=>{loadSatellite();loadEarthIntelligence()},music:loadSymphonyContext})[S.tab]?.()}


/* Numerically validated NASA POWER series + optional SRTM point elevation. */
async function loadEarthIntelligence(elevation=false,refresh=false){
 const el=$('#earthIntelligenceResults');if(!el)return;
 const fieldId=S.extraField;
 el.innerHTML='<p class="mut">Requesting NASA POWER daily data…</p>';
 try{
  const r=await api(`/fields/${fieldId}/earth-intelligence?days=365&elevation=${elevation}&refresh=${refresh}`);
  if(S.extraField!==fieldId||!$('#earthIntelligenceResults'))return;
  const p=r.data?.POWER,inds=p?.indicators||{},e=r.data?.SRTM;
  el.innerHTML=`<div class="row sb"><b>NASA Earth Intelligence</b><div class="row"><button class="btn o s" onclick="loadEarthIntelligence(true,true)">+ SRTM elevation</button><button class="btn o s" onclick="loadEarthIntelligence(false,true)">Refresh</button></div></div>`+
  (p?`<div class="mut">NASA POWER · UTC daily · ${esc(p.period.first_observation)}–${esc(p.period.last_observation)} · ${p.period.valid_days} valid days</div><div class="key-stats"><span>Period rain <b>${inds.rain_total_mm} mm</b></span><span>Mean temperature <b>${inds.mean_temp_c}°C</b></span><span>Dry days (&lt;1 mm) <b>${inds.dry_days_under_1mm}</b></span><span>Heavy rain days (≥20 mm) <b>${inds.heavy_rain_days_20mm}</b></span><span>Frost days <b>${inds.frost_days_min_le_0c??'n/a'}</b></span><span>Heat days <b>${inds.heat_days_max_ge_35c??'n/a'}</b></span></div>${p.monthly.length>1?`<b>Monthly rainfall, mm</b>${bars(p.monthly.map(x=>x.rain_mm),p.monthly.map(x=>x.month.slice(5)))}`:''}<p class="footnote">${p.limitations.map(esc).join(' · ')}</p>`:'<div class="warn">NASA POWER unavailable. No synthetic data used for this panel.</div>')+
  (e?`<p class="mut">SRTM point elevation: <b>${e.elevation_m} m</b> · third-party OpenTopoData mirror · ~90 m resolution. Not a field slope measurement.</p>`:'')+
  Object.entries(r.unavailable||{}).map(([k,v])=>`<p class="warn">${esc(k)}: ${esc(v)}</p>`).join('')+
  `<details><summary>Dataset availability and limitations</summary>${Object.entries(r.catalog).map(([k,v])=>`<p class="mut"><b>${esc(k)}</b>: ${esc(v)}</p>`).join('')}</details><div class="row"><button class="btn o s" onclick="refreshClimateSnapshot()">Update rotation baseline from NASA POWER</button></div>`;
 }catch(e){if(S.extraField===fieldId&&$('#earthIntelligenceResults'))$('#earthIntelligenceResults').innerHTML=`<div class="warn">NASA request failed: ${esc(e.message)}. Existing data has not been changed.</div>`}
}
async function refreshClimateSnapshot(){await tryit(async()=>{const f=S.extraField;const r=await api(`/fields/${f}/refresh-climate`,{b:{}});await load();toast(r.snapshot?.metrics?.simulated?'POWER unavailable — baseline is SIMULATED':'NASA POWER climate baseline updated');await loadEarthIntelligence();})}

async function loadNasaLayers(){
 const product=$('#nasaProduct')?.value, el=$('#nasaLayer'), info=$('#nasaCatalogInfo');
 if(!el||!info)return;
 el.innerHTML='<option value="">Select a verified NASA layer</option>';
 if(!product){info.textContent='Default MODIS NDVI extraction selected.';return}
 info.textContent='Checking live AppEEARS layer catalog…';
 try{
  const r=await api(`/fields/${S.extraField}/satellite/catalog?product=${encodeURIComponent(product)}`);
  const raw=r.layers;const names=Array.isArray(raw)?raw.map(x=>x.Layer||x.layer).filter(Boolean):Object.keys(raw||{});
  const matches=names.filter(x=>typeof x==='string'&&/soil|sm_root|moisture|lst|temp|surface/i.test(x)).slice(0,80);
  el.innerHTML='<option value="">Select a verified NASA layer</option>'+matches.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join('');
  info.textContent=matches.length?`${matches.length} candidate layers retrieved from NASA. Availability at your field and dates is not guaranteed.`:'No suitable soil-moisture or temperature layers found for this collection.';
 }catch(e){info.textContent='NASA layer catalog unavailable: '+e.message}
}
