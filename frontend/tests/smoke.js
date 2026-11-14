/* Minimal DOM-less template smoke test for the 13 navigation destinations.
   Network-backed content requires integration tests in a real browser. */
const fs=require('fs'),vm=require('vm'),path=require('path');
const els={};
function el(name){return els[name]||(els[name]={innerHTML:'',style:{},dataset:{},textContent:'',classList:{add(){},remove(){},toggle(){}},insertAdjacentHTML(pos,html){this.innerHTML+=html},remove(){},oninput:null,onclick:null,getContext(){return {clearRect(){},fillRect(){}}},getCanvas(){return {style:{}}}})}
const context={console,window:{maplibregl:null},document:{querySelector:el,querySelectorAll:()=>[],getElementById:el,documentElement:{dataset:{}}},localStorage:{tok:''},Audio:class{constructor(){this.paused=true;this.duration=100;this.src='';this.volume=.8} play(){return Promise.resolve()} pause(){}},AudioContext:class{resume(){}createMediaElementSource(){return {connect(){}}}createAnalyser(){return {fftSize:64,frequencyBinCount:16,getByteFrequencyData(){},connect(){}}}},requestAnimationFrame(){},setTimeout(){},clearTimeout(){},setInterval(){},fetch:async()=>({ok:true,json:async()=>[]})};
vm.createContext(context);
const root=path.join(__dirname,'..');
vm.runInContext(fs.readFileSync(path.join(root,'features.js'),'utf8'),context);
vm.runInContext(fs.readFileSync(path.join(root,'app.js'),'utf8'),context);
const m={rain_mm:450,temp_c:13,wetness:.41,rain_cv:.9,trend:.05,ndvi:null,simulated:true,source:'SIMULATED',last_obs:null,monthly:Array.from({length:12},(_,i)=>({m:'2026-'+String(i+1).padStart(2,'0'),rain:30,temp:15,wet:.4}))};
const field={id:1,name:'North',area_ha:110,soil:'Loam',soil_source:'farmer-provided',crops:['2023 wheat','2024 pea','2025 barley'],lat:43.2,lon:76.8,polygon:[[76.8,43.2],[76.81,43.2],[76.81,43.21]],snapshots:[{id:1,label:'now',metrics:m,harmony:80,level:'EXCELLENT',comps:[]}]};
const farm={id:1,name:'Test Farm',region:'Kazakhstan',lat:43.2,lon:76.8};
vm.runInContext(`S.scr='app';S.me=${JSON.stringify({user:{id:1,name:'Tester'},farm,fields:[field]})};S.known={};S.matches=[];S.disc=[]`,context);
let checked=0;
for(const name of ['home','earth','fields','doctor','weather','rot','co','match','chat','feed','music','knowledge','reports']){
 try{vm.runInContext(`S.tab='${name}';draw()`,context);const html=el('#main').innerHTML;if(!html||!html.includes('<'))throw Error('Empty view');checked++}
 catch(e){console.error(name,e);process.exitCode=1}
}
console.log(`Frontend static navigation smoke: ${checked}/13 sections rendered`);
