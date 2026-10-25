// Pure in-memory DOM test: no browser, networking, external resources or file navigation.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const html=fs.readFileSync('dashboard.html','utf8');
class Element{
 constructor(tag){this.tag=tag;this.children=[];this.style={};this.listeners={};this.attributes={};this.value='';this.textContent='';}
 append(...nodes){this.children.push(...nodes);if(this.tag==='select'&&!this.value&&this.children.length)this.value=this.children[0].value;}
 replaceChildren(...nodes){this.children=[];if(this.tag==='select')this.value='';this.append(...nodes);}
 setAttribute(k,v){this.attributes[k]=String(v)}
 addEventListener(k,fn){this.listeners[k]=fn}
}
const ids={};for(const m of html.matchAll(/<([a-z]+)[^>]*\bid="([^"]+)"[^>]*>/g))ids[m[2]]=new Element(m[1]);
ids['study-data'].textContent=html.match(/<script id="study-data" type="application\/json">([\s\S]*?)<\/script>/)[1];
ids.caseTable.tBodies=[new Element('tbody')];ids.seasonSelect.value='2023';
const document={getElementById:id=>ids[id]||null,createElement:tag=>new Element(tag),createElementNS:(ns,tag)=>new Element(tag),createTextNode:text=>({textContent:text})};
const context=vm.createContext({document,console});
const code=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]).join('\n');
new vm.Script(code).runInContext(context);
assert.equal(ids.caseSelect.children.length,10);assert.equal(ids.caseTable.tBodies[0].children.length,10);
assert.equal(ids.caseMetric.textContent,'1 / 8');
ids.caseSelect.value='tamu_2023';ids.caseSelect.listeners.change();
assert(ids.caseMeta.textContent.includes('insufficient'));
assert(ids.caseChart.src==='charts/tamu_2023.png');
assert(fs.existsSync(path.join('.',ids.caseChart.src)));
ids.seasonSelect.value='2022';ids.seasonSelect.listeners.change();ids.teamSelect.value='Nebraska';ids.teamSelect.listeners.change();
assert(ids.teamRank.textContent.includes('2022'));
assert.equal(ids.heatmap.children[1].children.length,4);
assert(ids.heatmap.children[1].children.every(row=>row.children.length===13));
const circles=ids.scatter.children.filter(n=>n.tag==='circle');assert(circles.length>120);
assert(circles.every(c=>+c.attributes.cx>=80&&+c.attributes.cx<=1025&&+c.attributes.cy>=35&&+c.attributes.cy<=335));
circles[0].listeners.click();assert(ids.scatterDetail.textContent.includes('drives'));
const payload=JSON.parse(ids['study-data'].textContent);for(const c of payload.cases)assert(fs.existsSync(`charts/${c.case_id}.png`));
console.log('PASS: script execution in isolated DOM harness; all case/season/team changes, table/heatmap cells, scatter selection, point bounds, and chart asset paths. Browser rendering NOT verified.');
