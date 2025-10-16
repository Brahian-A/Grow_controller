export function drawLine(canvas, values, color="#2f6b31"){
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const vals = values?.length ? values : [0];
  const min = Math.min(...vals), max = Math.max(...vals);
  const H = canvas.height, W = canvas.width;
  const y = v => (H-10) - ((v-min)/Math.max(1,(max-min)))*(H-20);
  ctx.clearRect(0,0,W,H);
  ctx.beginPath();
  vals.forEach((v,i)=>{
    const x = 10 + i*((W-20)/Math.max(1,vals.length-1));
    i ? ctx.lineTo(x,y(v)) : ctx.moveTo(x,y(v));
  });
  ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.stroke();
}
