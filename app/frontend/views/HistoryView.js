import { mount } from "../core/dom.js";
import { getHistory } from "../api/index.js";
import { drawLine } from "../ui/Chart.js";

export default function HistoryView(container) {
  const wrap = document.createElement("div");
  wrap.className = "HistoryView";
  wrap.innerHTML = `
    <div class="Graficas">
      <section class="card">
        <h3>Temperatura últimas 24h</h3>
        <canvas
          id="c1"
          width="360"
          height="120"
          role="img"
          aria-label="Gráfico de temperatura en las últimas 24 horas"
        ></canvas>
      </section>

      <section class="card">
        <h3>Humedad ambiente últimas 24h</h3>
        <canvas
          id="c2"
          width="360"
          height="120"
          role="img"
          aria-label="Gráfico de humedad ambiente en las últimas 24 horas"
        ></canvas>
      </section>

      <section class="card">
        <h3>Humedad de suelo últimas 24h</h3>
        <canvas
          id="c3"
          width="360"
          height="120"
          role="img"
          aria-label="Gráfico de humedad de suelo en las últimas 24 horas"
        ></canvas>
      </section>
    </div>

    <section class="card date-filter" role="region" aria-labelledby="csv-export-title">
      <h3 id="csv-export-title">Exportar CSV por rango</h3>
      <div class="controls" style="display:grid; gap:8px;">
        <label for="csv-desde">Desde</label>
        <input
          type="text"
          id="csv-desde"
          placeholder="YYYY-MM-DD"
          inputmode="numeric"
          autocomplete="off"
        >

        <label for="csv-hasta">Hasta</label>
        <input
          type="text"
          id="csv-hasta"
          placeholder="YYYY-MM-DD"
          inputmode="numeric"
          autocomplete="off"
        >

        <button id="btn-exportar-csv" type="button">
          Descargar CSV
        </button>

        <div
          id="csv-status"
          role="status"
          aria-live="polite"
          style="font-size:12px;color:#6b7280;"
        ></div>
      </div>
    </section>
  `;
  mount(container, wrap);

  const c1 = wrap.querySelector("#c1");
  const c2 = wrap.querySelector("#c2");
  const c3 = wrap.querySelector("#c3");

  const fpDesde = flatpickr("#csv-desde", {
    dateFormat: "Y-m-d",
    locale: "es",
  });
  const fpHasta = flatpickr("#csv-hasta", {
    dateFormat: "Y-m-d",
    locale: "es",
  });

  const hoy = new Date();
  const y = hoy.getFullYear();
  const m = hoy.getMonth();
  const d = hoy.getDate();
  fpHasta.setDate(new Date(y, m, d));
  fpDesde.setDate(new Date(y, m, d - 7));

  const btnCsv = wrap.querySelector("#btn-exportar-csv");
  const statusCsv = wrap.querySelector("#csv-status");

  btnCsv.addEventListener("click", async () => {
    const desde = document.getElementById("csv-desde").value;
    const hasta = document.getElementById("csv-hasta").value;

    if (!desde || !hasta) {
      statusCsv.textContent = "Elegí ambas fechas.";
      return;
    }
    if (hasta < desde) {
      statusCsv.textContent = "'Hasta' debe ser igual o posterior a 'Desde'.";
      return;
    }

    try {
      btnCsv.disabled = true;
      statusCsv.textContent = "Generando CSV…";

      const url = `/api/v1/lecturas/csv?desde=${encodeURIComponent(
        desde
      )}&hasta=${encodeURIComponent(hasta)}`;

      const res = await fetch(url, { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();

      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `lecturas_${desde}_a_${hasta}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(a.href);

      statusCsv.textContent = "CSV descargado ✅";
    } catch (e) {
      console.error(e);
      statusCsv.textContent = "No se pudo generar el CSV.";
    } finally {
      btnCsv.disabled = false;
      setTimeout(() => {
        statusCsv.textContent = "";
      }, 2500);
    }
  });

  let timer = null;
  let running = true;

  async function refresh() {
    try {
      const history = (await getHistory()) || [];
      const last24 = history
        .slice(-24)
        .sort(
          (a, b) => new Date(a.fecha_hora) - new Date(b.fecha_hora)
        );

      drawLine(c1, last24.map((r) => r.temperatura));
      drawLine(c2, last24.map((r) => r.humedad));
      drawLine(c3, last24.map((r) => r.humedad_suelo));
    } catch (e) {
    } finally {
      if (running) timer = setTimeout(refresh, 5000);
    }
  }

  const onEspChanged = () => {
    if (timer) clearTimeout(timer);
    refresh();
  };
  window.addEventListener("esp:changed", onEspChanged, { passive: true });

  refresh();

  return () => {
    running = false;
    if (timer) clearTimeout(timer);
    window.removeEventListener("esp:changed", onEspChanged);
  };
}
