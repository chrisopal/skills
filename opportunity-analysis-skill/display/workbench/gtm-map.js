(function () {
  'use strict';
  const clean = (name) => String(name || '').replace(/(特别行政区|维吾尔自治区|壮族自治区|回族自治区|自治区|省|市)$/u, '');
  const rings = (geometry) => geometry.type === 'Polygon' ? geometry.coordinates : geometry.type === 'MultiPolygon' ? geometry.coordinates.flat() : [];
  function contains(point, ring) {
    let inside = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [x, y] = ring[i], [a, b] = ring[j];
      if ((y > point[1]) !== (b > point[1]) && point[0] < (a - x) * (point[1] - y) / (b - y) + x) inside = !inside;
    }
    return inside;
  }
  function provinceOf(item, data) {
    const provinces = data.features.filter((f) => f.name);
    const explicit = provinces.find((f) => clean(item.province || item.region) === clean(f.name));
    if (explicit) return explicit.code;
    const city = clean(item.city);
    if (city) {
      const direct = provinces.find((f) => clean(f.name) === city);
      if (direct) return direct.code;
      for (const [code, rows] of Object.entries(data.cities)) if (rows.some((row) => clean(row.name) === city)) return code;
    }
    if (item.location) {
      const point = [item.location.lon, item.location.lat];
      for (const feature of provinces) if (rings(feature.geometry).some((ring) => contains(point, ring))) return feature.code;
    }
    return '';
  }
  function fits(item, province, city, data) {
    if (!province) return true;
    if (provinceOf(item, data) !== province) return false;
    if (!city) return true;
    const child = (data.cities[province] || []).find((c) => c.code === city);
    return !!child && clean(item.city) === clean(child.name);
  }
  function projection(bounds, box) {
    // Mercator latitude; uniform scale preserves the shape at every drill-down.
    const merc = (lat) => Math.log(Math.tan(Math.PI / 4 + lat * Math.PI / 360)) * 180 / Math.PI;
    const [west, south, east, north] = bounds, low = merc(south), high = merc(north);
    const scale = Math.min(box.w / (east - west), box.h / (high - low));
    return ([lon, lat]) => [box.x + box.w / 2 + (lon - (west + east) / 2) * scale, box.y + box.h / 2 - (merc(lat) - (low + high) / 2) * scale];
  }
  function path(geometry, project) {
    return rings(geometry).map((ring) => ring.map((p, i) => (i ? 'L' : 'M') + project(p).map((v) => v.toFixed(2)).join(',')).join('') + 'Z').join('');
  }
  function boundsOf(feature) {
    const points = rings(feature.geometry).flat().filter((p) => p[1] >= 16);
    const xs = points.map((p) => p[0]), ys = points.map((p) => p[1]);
    const w = Math.max(...xs) - Math.min(...xs), h = Math.max(...ys) - Math.min(...ys);
    return [Math.min(...xs) - Math.max(.15, w * .09), Math.min(...ys) - Math.max(.15, h * .09), Math.max(...xs) + Math.max(.15, w * .09), Math.max(...ys) + Math.max(.15, h * .09)];
  }
  function render({ svg, data, province, city, items, selected, zoom, onProvince, onCity, onObject }) {
    svg.replaceChildren(); const ns = 'http://www.w3.org/2000/svg';
    const node = (tag, attrs, text) => { const n = document.createElementNS(ns, tag); Object.entries(attrs || {}).forEach(([k, v]) => n.setAttribute(k, v)); if (text != null) n.textContent = text; return n; };
    const activate = (el, fn) => { el.addEventListener('click', fn); el.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fn(); } }); };
    const feature = data.features.find((f) => f.code === province);
    let bounds = feature ? boundsOf(feature) : [72, 16, 137, 55];
    if (zoom > 1) {
      const focusedCity = (data.cities[province] || []).find((c) => c.code === city);
      const center = focusedCity ? focusedCity.center : [(bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2];
      const w = (bounds[2] - bounds[0]) / zoom, h = (bounds[3] - bounds[1]) / zoom;
      bounds = [center[0] - w / 2, center[1] - h / 2, center[0] + w / 2, center[1] + h / 2];
    }
    const project = projection(bounds, {x:25,y:25,w:910,h:550});
    const defs = node('defs'), clip = node('clipPath',{id:'china-map-clip'}); clip.append(node('rect',{x:5,y:5,width:950,height:600})); defs.append(clip); svg.append(defs);
    const layer = node('g',{'clip-path':'url(#china-map-clip)'}); svg.append(layer);
    const counts = {}; items.forEach((item) => { const code = provinceOf(item, data); counts[code] = (counts[code] || 0) + 1; });
    data.features.forEach((f) => {
      const p = node('path',{d:path(f.geometry,project),class:'gtm-province' + (f.code === province ? ' is-active' : '') + (counts[f.code] ? ' has-targets' : '')});
      if (f.name) { p.setAttribute('role','button'); p.setAttribute('tabindex','0'); p.setAttribute('aria-label',f.name + '，' + (counts[f.code] || 0) + '个推广对象'); p.append(node('title',{},f.name)); activate(p,()=>onProvince(f.code)); }
      layer.append(p);
    });
    if (!province) {
      const offsets = {'110000':[-35,-19],'120000':[37,-6],'310000':[36,0],'810000':[49,18],'820000':[-24,20],'440000':[0,-20],'460000':[-10,7]};
      data.features.filter((f)=>f.name).forEach((f)=>{
        const center = f.code === '620000' ? [103.5,38.8] : f.center;
        const [x,y]=project(center), [dx,dy]=offsets[f.code] || [0,0];
        if (dx || dy) layer.append(node('line',{x1:x,y1:y,x2:x+dx,y2:y+dy,class:'gtm-label-connector'}));
        const label=node('text',{x:x+dx,y:y+dy,class:'gtm-province-label','text-anchor':'middle'},clean(f.name));
        activate(label,()=>onProvince(f.code)); layer.append(label);
      });
      const inset=node('g',{'aria-label':'南海诸岛附图'}); inset.append(node('rect',{x:772,y:393,width:165,height:200,class:'gtm-inset-bg'}));
      const ip=projection([106,2,124,25],{x:780,y:416,w:148,h:167});
      data.features.forEach((f)=>{ const clipped={...f.geometry,coordinates:f.geometry.coordinates}; const d=path(clipped,ip); inset.append(node('path',{d,class:'gtm-inset-path'})); });
      // Clip inset geometry to its panel; preserve source islands and boundary detail.
      const ic=node('clipPath',{id:'china-inset-clip'});ic.append(node('rect',{x:775,y:416,width:158,height:175}));defs.append(ic);
      Array.from(inset.querySelectorAll('path')).forEach((p)=>p.setAttribute('clip-path','url(#china-inset-clip)'));
      inset.append(node('text',{x:854,y:410,'text-anchor':'middle',class:'gtm-inset-label'},'南海诸岛'));svg.append(inset);
    } else {
      const occupied=[];
      (data.cities[province] || []).forEach((c)=>{
        const [x,y]=project(c.center); if (x<10 || x>945 || y<15 || y>580) return;
        let ly=y-10; const width=c.name.length*12+8;
        for(let step=0;step<25 && occupied.some((r)=>Math.abs(r.y-ly)<17 && Math.abs(r.x-x)<(r.w+width)/2);step++) ly+=18;
        ly=Math.min(580,Math.max(20,ly));occupied.push({x,y:ly,w:width});
        const g=node('g',{class:'gtm-admin-city'+(c.code===city?' is-active':'')});
        g.append(node('line',{x1:x,y1:y,x2:x,y2:ly,class:'gtm-label-connector'}),node('circle',{cx:x,cy:y,r:c.code===city?5:3}));
        const label=node('text',{x,y:ly,'text-anchor':'middle',role:'button',tabindex:'0','aria-label':c.name+'，查看推广对象'},c.name);
        activate(label,()=>onCity(c.code)); g.append(label);layer.append(g);
      });
    }
    const groups=new Map();items.filter((i)=>i.location && Number.isFinite(i.location.lon) && Number.isFinite(i.location.lat)).forEach((i)=>{const key=i.location.lon+','+i.location.lat;if(!groups.has(key))groups.set(key,[]);groups.get(key).push(i);});
    groups.forEach((entries)=>{
      const item=entries.find((i)=>i.key===selected)||entries[0], [x,y]=project([item.location.lon,item.location.lat]);
      if(x<10||x>945||y<10||y>585)return;
      const g=node('g',{class:'gtm-map-point'+(entries.some((i)=>i.object_type==='company')?' company':' event')+(entries.some((i)=>i.key===selected)?' is-selected':'')});
      const p=node('circle',{cx:x,cy:y,r:entries.some((i)=>i.key===selected)?8:6,tabindex:'0',role:'button','aria-label':item.city+'，'+entries.length+'个对象'});
      activate(p,()=>onObject(item));g.append(p,node('title',{},item.city+' · '+entries.length+'个推广对象'));
      if (province) g.append(node('text',{x:x+11,y:y+21,class:'gtm-object-label'},entries.length+'个对象')); layer.append(g);
    });
    const caption=feature ? feature.name+' · '+(data.cities[province]||[]).length+'个下辖单位标注' : '中国 · 34个省级区域';
    svg.append(node('text',{x:26,y:610,class:'gtm-map-caption'},caption));
  }
  window.GTMMap=Object.freeze({clean,contains,provinceOf,fits,projection,path,boundsOf,render});
}());
