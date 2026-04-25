import { ref, nextTick } from 'vue';

export function useLog(containerRef, maxLogs = 200) {
  const logs = ref([]);

  const addLog = (message, type = 'info') => {
    const time = new Date().toLocaleTimeString('zh-CN', { hour12: false });
    logs.value.push({ time, message, type });
    if (logs.value.length > maxLogs) logs.value.shift();
    nextTick(() => {
      if (containerRef?.value) containerRef.value.scrollTop = containerRef.value.scrollHeight;
    });
  };

  const clearLogs = () => {
    logs.value = [];
    addLog('Terminal buffer cleared.', 'info');
  };

  return { logs, addLog, clearLogs };
}
