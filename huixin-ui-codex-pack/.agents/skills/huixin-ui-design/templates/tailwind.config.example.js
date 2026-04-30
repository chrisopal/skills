/** @type {import('tailwindcss').Config} */
module.exports = {
  theme: {
    extend: {
      colors: {
        hx: {
          primary: "#00405C",
          action: "#0097BA",
          selected: "#CCF5FF",
          green: "#A5D867",
          success: "#2BA471",
          warning: "#E37318",
          error: "#D54941",
          borderA: "#DBDFE7",
          borderB: "#E3E7EE",
          bgA: "#F0F2F5",
          bgB: "#F5F7FA",
          title: "#333333",
          text: "#666666",
          muted: "#999999"
        }
      },
      fontFamily: {
        hx: ["HarmonyOS Sans", "Source Han Sans SC", "思源黑体", "Microsoft YaHei", "Arial", "sans-serif"],
        hxNumber: ["D-DIN-PRO", "DIN", "HarmonyOS Sans", "Arial", "sans-serif"]
      },
      borderRadius: {
        hxControl: "3px",
        hxCard: "6px"
      }
    }
  }
};
