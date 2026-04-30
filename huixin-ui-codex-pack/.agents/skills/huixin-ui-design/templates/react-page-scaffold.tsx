import React from "react";
import "./react-page-scaffold.css";

type Metric = {
  label: string;
  value: string;
  delta?: string;
  status?: "success" | "warning" | "error" | "normal";
};

const metrics: Metric[] = [
  { label: "今日任务", value: "128", delta: "+12%", status: "success" },
  { label: "待处理异常", value: "16", delta: "-3", status: "warning" },
  { label: "设备在线率", value: "98.6%", delta: "+0.8%", status: "success" },
  { label: "交付准时率", value: "94.2%", delta: "-1.1%", status: "normal" }
];

const navItems = [
  { id: "dashboard", label: "仪表盘", href: "/dashboard" },
  { id: "projects", label: "项目列表", href: "/projects" },
  { id: "forms", label: "表单页", href: "/forms" },
  { id: "details", label: "详情页", href: "/details" },
  { id: "settings", label: "系统设置", href: "/settings" }
];

const rows = [
  { id: "project-a", name: "项目A", tag: "默认标签", owner: "张三", status: "进行中" },
  { id: "project-b", name: "项目B", tag: "默认标签", owner: "李四", status: "待确认" },
  { id: "project-c", name: "项目C", tag: "默认标签", owner: "王五", status: "已完成" }
];

function deltaClassName(status?: Metric["status"]) {
  return `hx-metric-delta hx-metric-delta-${status || "normal"}`;
}

export default function HuixinAdminPageScaffold() {
  return (
    <div className="hx-admin-shell">
      <aside className="hx-admin-sidebar">
        <div className="hx-sidebar-logo">慧新全智</div>
        <nav className="hx-sidebar-nav" aria-label="主导航">
          {navItems.map((item, index) => (
            <a
              key={item.id}
              href={item.href}
              className={index === 0 ? "hx-sidebar-link hx-sidebar-link-active" : "hx-sidebar-link"}
            >
              {item.label}
            </a>
          ))}
        </nav>
      </aside>

      <main className="hx-admin-main">
        <header className="hx-page-header">
          <div>
            <h1 className="hx-page-title">项目运营看板</h1>
            <p className="hx-page-description">
              遵循 Huixin UI Design 2.0 的中后台页面脚手架
            </p>
          </div>
          <button className="hx-btn hx-btn-primary">新建任务</button>
        </header>

        <section className="hx-metric-grid">
          {metrics.map((metric) => (
            <article className="hx-card" key={metric.label}>
              <div className="hx-metric-label">{metric.label}</div>
              <div className="hx-number hx-metric-value">
                {metric.value}
              </div>
              {metric.delta ? (
                <div className={deltaClassName(metric.status)}>{metric.delta}</div>
              ) : null}
            </article>
          ))}
        </section>

        <section className="hx-card">
          <div className="hx-table-toolbar">
            <h2 className="hx-card-title">项目列表</h2>
            <input className="hx-input" placeholder="请输入搜索内容" aria-label="搜索项目" />
          </div>

          <div className="hx-table-scroll">
            <table className="hx-table">
              <thead>
                <tr>
                  {["项目名称", "标签", "负责人", "状态", "操作"].map((head) => (
                    <th key={head}>{head}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td className="hx-table-title-cell">{row.name}</td>
                    <td><span className="hx-tag">{row.tag}</span></td>
                    <td>{row.owner}</td>
                    <td>{row.status}</td>
                    <td>
                      <button className="hx-btn hx-btn-outline">管理</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}
