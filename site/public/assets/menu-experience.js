(() => {
  const dataNode=document.getElementById('bravis-menu-data');
  const dialog=document.getElementById('menu-lightbox');
  if(!dataNode || !dialog || typeof dialog.showModal!=='function') return;
  let sections;
  try{sections=JSON.parse(dataNode.textContent)}catch{return}
  let section=0,page=0;
  const title=document.getElementById('menu-lightbox-title');
  const count=document.getElementById('menu-lightbox-counter');
  const image=document.getElementById('menu-lightbox-image');
  const prev=document.getElementById('menu-lightbox-prev');
  const next=document.getElementById('menu-lightbox-next');
  let focusBefore=null;
  function draw(){
    const choice=sections[section];
    if(!choice || !choice.pages || !choice.pages.length)return;
    page=Math.max(0,Math.min(choice.pages.length-1,page));
    title.textContent=choice.title;
    count.textContent=(page+1)+' / '+choice.pages.length;
    image.src=choice.pages[page];
    image.alt=choice.title+', страница '+(page+1);
    const singlePage=choice.pages.length===1;
    dialog.classList.toggle('menu-lightbox--single', singlePage);
    prev.hidden=singlePage;
    next.hidden=singlePage;
    prev.disabled=page===0;
    next.disabled=page===choice.pages.length-1;
  }
  document.querySelectorAll('[data-menu-index]').forEach(link=>link.addEventListener('click',event=>{
    const index=Number(link.dataset.menuIndex);
    if(!Number.isInteger(index)||index<0||index>=sections.length)return;
    event.preventDefault();
    section=index;page=0;focusBefore=link;draw();dialog.showModal();
  }));
  prev.addEventListener('click',()=>{page--;draw()});
  next.addEventListener('click',()=>{page++;draw()});
  document.getElementById('menu-lightbox-close').addEventListener('click',()=>dialog.close());
  dialog.addEventListener('close',()=>{image.removeAttribute('src');if(focusBefore)focusBefore.focus()});
  dialog.addEventListener('click',e=>{if(e.target===dialog)dialog.close()});
  dialog.addEventListener('keydown',e=>{
    if(e.key==='ArrowLeft'){e.preventDefault();page--;draw()}
    if(e.key==='ArrowRight'){e.preventDefault();page++;draw()}
  });
})();