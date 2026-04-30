import type { ThemeConfig } from "antd";

export const huixinAntdTheme: ThemeConfig = {
  token: {
    colorPrimary: "#0097BA",
    colorSuccess: "#2BA471",
    colorWarning: "#E37318",
    colorError: "#D54941",
    colorText: "#666666",
    colorTextHeading: "#333333",
    colorTextSecondary: "#999999",
    colorBorder: "#DBDFE7",
    colorSplit: "#E3E7EE",
    colorBgLayout: "#F0F2F5",
    colorBgContainer: "#FFFFFF",
    fontFamily: "HarmonyOS Sans, Source Han Sans SC, 思源黑体, Microsoft YaHei, Arial, sans-serif",
    fontSize: 14,
    lineHeight: 22 / 14,
    borderRadius: 3,
    controlHeight: 32,
    padding: 16,
    paddingLG: 24,
    margin: 16,
    marginLG: 24
  },
  components: {
    Layout: {
      siderBg: "#00405C",
      triggerBg: "#00405C",
      triggerColor: "#FFFFFF"
    },
    Menu: {
      darkItemBg: "#00405C",
      darkItemSelectedBg: "#0097BA",
      darkItemColor: "rgba(255,255,255,0.82)",
      darkItemSelectedColor: "#FFFFFF"
    },
    Button: {
      controlHeight: 32,
      borderRadius: 3,
      paddingInline: 16
    },
    Input: {
      controlHeight: 32,
      borderRadius: 3,
      paddingInline: 8
    },
    Card: {
      borderRadiusLG: 6,
      paddingLG: 24
    },
    Tag: {
      borderRadiusSM: 3,
      fontSizeSM: 12
    }
  }
};
