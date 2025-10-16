import { el } from "../core/dom.js";
export function Card(title, contentNode){
  return el("section", { class:"card" },
    el("h3", { innerHTML: title }),
    contentNode
  );
}
