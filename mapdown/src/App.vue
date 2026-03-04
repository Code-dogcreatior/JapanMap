<template>
   <div class="saas-app-layout">
     <!-- 全局顶部导航栏 -->
     <nav class="global-nav">
       <div class="nav-brand">
         <div class="logo-box">
           <svg fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
             <path stroke-linecap="round" stroke-linejoin="round" d="M9 6.75V15m6-6v8.25m.503 3.498l4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 00-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0z" />
           </svg>
         </div>
         <span class="brand-text">GSI Map Engine <span>Pro</span></span>
       </div>
 
       <div class="nav-tabs">
         <button 
           class="tab-btn" 
           :class="{ active: currentTab === 'download' }"
           @click="currentTab = 'download'"
         >
           <svg class="tab-icon" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" /></svg>
           瓦片下载引擎
         </button>
         <button 
           class="tab-btn" 
           :class="{ active: currentTab === 'viewer' }"
           @click="currentTab = 'viewer'"
         >
           <svg class="tab-icon" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 3.75h.008v.008h-.008v-.008zm0 3h.008v.008h-.008v-.008zm0 3h.008v.008h-.008v-.008z" /></svg>
           本地地图渲染
         </button>
       </div>
 
       <div class="nav-actions">
         <div class="user-avatar">Admin</div>
       </div>
     </nav>
 
     <!-- 主体内容区（使用 KeepAlive 保持组件状态） -->
     <main class="app-content">
       <KeepAlive>
         <component :is="currentComponent" />
       </KeepAlive>
     </main>
   </div>
 </template>
 
 <script setup>
 import { ref, computed } from 'vue';
 import DownloadEngine from './components/download.vue'; // 确保路径正确
 import LocalMapViewer from './components/LocalMapViewer.vue'; // 确保路径正确
 
 // 状态控制：'download' 或 'viewer'
 const currentTab = ref('download');
 
 const currentComponent = computed(() => {
   return currentTab.value === 'download' ? DownloadEngine : LocalMapViewer;
 });
 </script>
 
 <style scoped>
 .saas-app-layout {
   display: flex;
   flex-direction: column;
   height: 100vh;
   width: 100vw;
   overflow: hidden;
   background-color: #f8fafc;
   font-family: 'Inter', system-ui, -apple-system, sans-serif;
 }
 
 /* 顶部高级导航栏 */
 .global-nav {
   display: flex;
   align-items: center;
   justify-content: space-between;
   height: 64px;
   padding: 0 1.5rem;
   background: #ffffff;
   border-bottom: 1px solid #e2e8f0;
   box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
   z-index: 1000;
 }
 
 .nav-brand {
   display: flex;
   align-items: center;
   gap: 0.75rem;
   width: 280px;
 }
 
 .logo-box {
   width: 36px;
   height: 36px;
   background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%);
   color: white;
   border-radius: 8px;
   display: flex;
   align-items: center;
   justify-content: center;
 }
 
 .logo-box svg {
   width: 20px;
   height: 20px;
 }
 
 .brand-text {
   font-size: 1.125rem;
   font-weight: 700;
   color: #0f172a;
   letter-spacing: -0.025em;
 }
 
 .brand-text span {
   font-size: 0.75rem;
   background: #e0e7ff;
   color: #4f46e5;
   padding: 0.15rem 0.4rem;
   border-radius: 4px;
   vertical-align: top;
   margin-left: 0.25rem;
 }
 
 /* 导航切换按钮 */
 .nav-tabs {
   display: flex;
   gap: 1rem;
   background: #f1f5f9;
   padding: 0.35rem;
   border-radius: 10px;
 }
 
 .tab-btn {
   display: flex;
   align-items: center;
   gap: 0.5rem;
   padding: 0.5rem 1.25rem;
   border: none;
   border-radius: 6px;
   background: transparent;
   color: #64748b;
   font-size: 0.9rem;
   font-weight: 600;
   cursor: pointer;
   transition: all 0.2s ease;
 }
 
 .tab-icon {
   width: 18px;
   height: 18px;
 }
 
 .tab-btn:hover {
   color: #0f172a;
 }
 
 .tab-btn.active {
   background: #ffffff;
   color: #4f46e5;
   box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
 }
 
 .nav-actions {
   width: 280px;
   display: flex;
   justify-content: flex-end;
 }
 
 .user-avatar {
   background: #e2e8f0;
   color: #475569;
   font-size: 0.85rem;
   font-weight: 600;
   padding: 0.5rem 1rem;
   border-radius: 20px;
   border: 1px solid #cbd5e1;
 }
 
 /* 路由容器 */
 .app-content {
   flex: 1;
   position: relative;
   overflow: hidden;
 }
 </style>