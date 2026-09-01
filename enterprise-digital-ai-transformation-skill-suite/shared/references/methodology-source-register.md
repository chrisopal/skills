# 方法论来源登记

> 用途：记录 Skill Suite 方法论口径的公开来源。外部来源用于定义参考框架，不自动构成任何客户项目的事实或结论。

## 华为 4A

1. **华为企业业务：《华为ICT产品组合方案助力客户构建先进数字基础设施》**  
   公开口径明确列出企业 4A：BA 业务架构、AA 应用架构、IA 信息架构、TA 技术架构。  
   https://e.huawei.com/cn/news/2023/solutions/wan/build-advanced-digital-infrastructure

2. **华为技术：《AI ready的智云助力运营商数智化转型》**  
   将 TOGAF 企业架构描述为战略规划与 IT 建设之间的桥梁，并列出 BA、IA、AA、TA；同时提出在 4A 中融入 AI。  
   https://www.huawei.com/cn/huaweitech/publication/202401/ai-ready-cloud-intelligent-digital-transformation-carriers

3. **华为企业业务：《证券企业如何选择数字化转型的“同路人”》**  
   说明业务需求变化驱动业务架构变化，进一步影响应用架构，应用实现依托技术架构，用于支持 4A 跨域联动规则。  
   https://e.huawei.com/cn/blogs/industries/finance/2023/digital-transformation-of-the-securities-industry

## TOGAF / Enterprise Architecture

4. **The Open Group：TOGAF Standard**  
   作为本套件 Architecture Lifecycle、ADM、Gap、Migration Planning、Implementation Governance 的方法来源。  
   https://www.opengroup.org/togaf

5. **The Open Group：How the ArchiMate Language and the TOGAF Standard Complement Each Other**  
   明确 business、application、data、technology 架构域及从战略、能力、架构到工作包的追溯逻辑。  
   https://help.opengroup.org/hc/en-us/articles/32115987894930-How-the-ArchiMate-Language-and-the-TOGAF-Standard-Complement-Each-Other

## 本套件采用的统一解释

- 企业架构内容模型采用华为 4A：`BA / IA / AA / TA`。
- TOGAF `Data Architecture` 映射到华为 `IA Information Architecture`；IA 同时覆盖信息、数据、语义、指标、元数据、Ontology 与知识。
- TOGAF/ADM 作为架构工作的生命周期与治理方法，不与 4A 争夺内容分类。
- Operating Model 是 BA 的业务设计源模型；共享价值流、能力、流程、组织、治理与 KPI Node ID。
- Integration、Security & Trust、AI & Knowledge、NFR & Resilience、Architecture Governance 是跨 4A 的横向视图，不增加第五个“A”。
