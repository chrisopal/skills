import React from "react";
import "./agent-console-page.css";

type AgentStatus = "running" | "idle" | "blocked";
type TaskPriority = "high" | "medium" | "low";

const agents: Array<{
  id: string;
  name: string;
  role: string;
  status: AgentStatus;
  load: string;
  loadLevel: "low" | "medium" | "high";
  queue: number;
}> = [
  { id: "agent-orchestrator", name: "总控智能体", role: "任务编排", status: "running", load: "76%", loadLevel: "high", queue: 12 },
  { id: "agent-inspector", name: "巡检智能体", role: "质量核验", status: "running", load: "48%", loadLevel: "medium", queue: 6 },
  { id: "agent-planner", name: "计划智能体", role: "方案拆解", status: "idle", load: "12%", loadLevel: "low", queue: 0 },
  { id: "agent-risk", name: "风控智能体", role: "异常识别", status: "blocked", load: "34%", loadLevel: "medium", queue: 3 }
];

const tasks: Array<{
  id: string;
  title: string;
  owner: string;
  priority: TaskPriority;
  progress: string;
  eta: string;
}> = [
  { id: "task-1048", title: "产线异常归因分析", owner: "巡检智能体", priority: "high", progress: "82%", eta: "预计 14:30 完成" },
  { id: "task-1049", title: "设备维保计划生成", owner: "计划智能体", priority: "medium", progress: "46%", eta: "预计 15:10 完成" },
  { id: "task-1050", title: "供应风险日报汇总", owner: "风控智能体", priority: "low", progress: "28%", eta: "等待数据同步" }
];

const events = [
  { id: "event-1", time: "13:42", title: "总控智能体完成任务拆解", detail: "已分配 5 个子任务至专用智能体" },
  { id: "event-2", time: "13:36", title: "巡检智能体发现异常趋势", detail: "注塑一线良率波动超过阈值" },
  { id: "event-3", time: "13:20", title: "风控智能体等待外部数据", detail: "供应商交付接口返回延迟" }
];

const statusText: Record<AgentStatus, string> = {
  running: "运行中",
  idle: "空闲",
  blocked: "阻塞"
};

const priorityText: Record<TaskPriority, string> = {
  high: "高",
  medium: "中",
  low: "低"
};

export default function HuixinAgentConsolePage() {
  return (
    <div className="hx-agent-console">
      <aside className="hx-console-sidebar">
        <div className="hx-console-logo">慧新全智</div>
        <nav className="hx-console-nav" aria-label="智能体控制台导航">
          {["控制台", "任务队列", "智能体", "知识库", "运行日志", "系统设置"].map((item, index) => (
            <a
              className={index === 0 ? "hx-console-nav-link hx-console-nav-link-active" : "hx-console-nav-link"}
              href={`/${item === "控制台" ? "console" : item}`}
              key={item}
            >
              {item}
            </a>
          ))}
        </nav>
      </aside>

      <main className="hx-console-main">
        <header className="hx-console-header">
          <div>
            <p className="hx-console-kicker">智能制造任务中枢</p>
            <h1 className="hx-console-title">智能体控制台</h1>
          </div>
          <div className="hx-console-actions">
            <button className="hx-btn hx-btn-outline" type="button">暂停调度</button>
            <button className="hx-btn hx-btn-primary" type="button">新建任务</button>
          </div>
        </header>

        <section className="hx-console-summary" aria-label="控制台概览">
          <article className="hx-summary-card">
            <span className="hx-summary-label">在线智能体</span>
            <strong className="hx-summary-value">24</strong>
            <span className="hx-summary-note hx-success-text">+3 本日新增</span>
          </article>
          <article className="hx-summary-card">
            <span className="hx-summary-label">运行中任务</span>
            <strong className="hx-summary-value">138</strong>
            <span className="hx-summary-note">平均响应 1.8s</span>
          </article>
          <article className="hx-summary-card">
            <span className="hx-summary-label">异常待处理</span>
            <strong className="hx-summary-value">7</strong>
            <span className="hx-summary-note hx-warning-text">2 项超过 SLA</span>
          </article>
          <article className="hx-summary-card">
            <span className="hx-summary-label">自动化完成率</span>
            <strong className="hx-summary-value">92.6%</strong>
            <span className="hx-summary-note hx-success-text">+4.2%</span>
          </article>
        </section>

        <section className="hx-console-layout">
          <div className="hx-console-left">
            <section className="hx-panel" aria-labelledby="agents-title">
              <div className="hx-panel-header">
                <h2 id="agents-title" className="hx-panel-title">智能体状态</h2>
                <button className="hx-btn hx-btn-outline" type="button">管理</button>
              </div>
              <div className="hx-agent-grid">
                {agents.map((agent) => (
                  <article className="hx-agent-card" key={agent.id}>
                    <div className="hx-agent-card-header">
                      <div>
                        <h3 className="hx-agent-name">{agent.name}</h3>
                        <p className="hx-agent-role">{agent.role}</p>
                      </div>
                      <span className={`hx-status hx-status-${agent.status}`}>{statusText[agent.status]}</span>
                    </div>
                    <div className="hx-agent-meter" aria-label={`${agent.name} 负载 ${agent.load}`}>
                      <span className={`hx-agent-meter-fill hx-agent-meter-fill-${agent.loadLevel}`} />
                    </div>
                    <div className="hx-agent-meta">
                      <span>负载 {agent.load}</span>
                      <span>队列 {agent.queue}</span>
                    </div>
                  </article>
                ))}
              </div>
            </section>

            <section className="hx-panel" aria-labelledby="tasks-title">
              <div className="hx-panel-header">
                <h2 id="tasks-title" className="hx-panel-title">任务队列</h2>
                <input className="hx-input" aria-label="搜索任务" placeholder="搜索任务编号或名称" />
              </div>
              <div className="hx-table-scroll">
                <table className="hx-console-table">
                  <thead>
                    <tr>
                      <th>任务</th>
                      <th>负责人</th>
                      <th>优先级</th>
                      <th>进度</th>
                      <th>预计完成</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tasks.map((task) => (
                      <tr key={task.id}>
                        <td>
                          <strong>{task.title}</strong>
                          <span>{task.id}</span>
                        </td>
                        <td>{task.owner}</td>
                        <td><span className={`hx-priority hx-priority-${task.priority}`}>{priorityText[task.priority]}</span></td>
                        <td>{task.progress}</td>
                        <td>{task.eta}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </div>

          <aside className="hx-console-right">
            <section className="hx-panel" aria-labelledby="runtime-title">
              <h2 id="runtime-title" className="hx-panel-title">运行态势</h2>
              <div className="hx-runtime-chart" aria-label="智能体运行态势图">
                <span className="hx-chart-bar hx-chart-bar-a" />
                <span className="hx-chart-bar hx-chart-bar-b" />
                <span className="hx-chart-bar hx-chart-bar-c" />
                <span className="hx-chart-bar hx-chart-bar-d" />
                <span className="hx-chart-bar hx-chart-bar-e" />
              </div>
              <div className="hx-runtime-legend">
                <span>吞吐 86%</span>
                <span>稳定性 97%</span>
              </div>
            </section>

            <section className="hx-panel" aria-labelledby="events-title">
              <h2 id="events-title" className="hx-panel-title">最新事件</h2>
              <ol className="hx-event-list">
                {events.map((event) => (
                  <li key={event.id}>
                    <time>{event.time}</time>
                    <div>
                      <strong>{event.title}</strong>
                      <p>{event.detail}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </section>
          </aside>
        </section>
      </main>
    </div>
  );
}
