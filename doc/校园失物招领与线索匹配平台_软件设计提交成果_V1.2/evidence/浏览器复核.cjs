// Optional rendering evidence; Node + Playwright + Sharp + a browser required.
// Usage: node 浏览器复核.cjs --modules <node_modules> --browser <executable>
// Main standard-library document checks do not require this environment.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {pathToFileURL}=require('url');
const args=process.argv.slice(2), arg=(name)=>args[args.indexOf(name)+1];
const modules=arg('--modules'), executable=arg('--browser');
if(!modules||!executable)throw Error('Provide --modules and --browser; no guessed environment');
const {chromium}=require(path.join(modules,'playwright'));
const sharp=require(path.join(modules,'sharp'));
const root=path.resolve(__dirname,'..'), preview=path.join(__dirname,'preview');
fs.mkdirSync(preview,{recursive:true});
const sha=(p)=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
(async()=>{
 for(const name of fs.readdirSync(path.join(root,'diagrams')))if(name.endsWith('.svg'))
   await sharp(path.join(root,'diagrams',name)).resize(1200).png().toFile(path.join(preview,name.replace('.svg','.png')));
 const browser=await chromium.launch({headless:true,executablePath:executable});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const doc=path.join(root,'01_软件设计文档_阅读打印版.html');
  await page.goto(pathToFileURL(doc).href);await page.addStyleTag({content:'html{scroll-behavior:auto!important}'});
  const observed=await page.evaluate(()=>({width:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth,sectionCount:document.querySelectorAll('h2').length,tableCount:document.querySelectorAll('table').length,svgCount:document.querySelectorAll('svg').length,missingTocTargets:[...document.querySelectorAll('nav a')].filter(a=>!document.querySelector(a.getAttribute('href'))).length,tableColumnMismatch:[...document.querySelectorAll('table')].map((t,i)=>({table:i,n:t.querySelectorAll('thead th').length,rows:[...t.querySelectorAll('tbody tr')].map(r=>r.children.length)})).filter(t=>t.rows.some(n=>n!==t.n)),svgTextOutside:[...document.querySelectorAll('svg text')].filter(t=>{const b=t.getBBox(),v=t.ownerSVGElement.viewBox.baseVal;return b.x<0||b.y<0||b.x+b.width>v.width||b.y+b.height>v.height}).map(t=>t.textContent)}));
  const targets=['3.6 共享','6.1.1 错误','6.3.1 T C','5.10 质量','9.5 易用','10.1 监测'];
  for(let i=0;i<targets.length;i++){
    const h=page.locator('h3').filter({hasText:targets[i]});
    await h.evaluate(e=>window.scrollTo(0,e.getBoundingClientRect().top+window.scrollY-30));
    await page.screenshot({path:path.join(preview,'修订章节'+String(i+1)+'.png')});
  }
  await page.setViewportSize({width:360,height:844});await page.evaluate(()=>window.scrollTo(0,0));
  await page.screenshot({path:path.join(preview,'360px首页.png')});
  observed.mobile=await page.evaluate(()=>({width:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth}));
  const passed=observed.width===observed.scroll&&observed.mobile.width===observed.mobile.scroll&&observed.missingTocTargets===0&&observed.tableColumnMismatch.length===0&&observed.svgTextOutside.length===0;
  const report={version:'SD V1.2',date:new Date().toISOString(),browserVersion:browser.version(),method:'本包浏览器复核.cjs，实际本地无窗口浏览器；全部表列数/目录/SVG边界；修订章节截图',observed,structurePassed:passed,visualReviewStatus:'PENDING',documentSha256:sha(path.join(root,'01_软件设计文档.md')),htmlSha256:sha(doc),scope:'仅设计文档阅读版/图表，不是N-04/N-05/N-08软件验收，也未全页打印PDF'};
  fs.writeFileSync(path.join(__dirname,'阅读版与图表检查.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify(report));
  if(!passed)throw Error('Rendering structure check failed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
