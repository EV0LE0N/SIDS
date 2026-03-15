import axios from 'axios';

const API_BASE_URL = '/api';

// 创建axios实例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  }
});

// 请求拦截器
apiClient.interceptors.request.use(
  config => {
    // 可以在这里添加token等认证信息
    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  response => {
    return response.data;
  },
  error => {
    console.error('API请求错误:', error);
    
    // 统一错误处理
    if (error.response) {
      // 服务器返回错误状态码
      const { status, data } = error.response;
      let message = `请求失败 (${status})`;
      
      if (data && data.detail) {
        message = data.detail;
      } else if (status === 404) {
        message = '接口不存在';
      } else if (status === 500) {
        message = '服务器内部错误';
      }
      
      return Promise.reject(new Error(message));
    } else if (error.request) {
      // 请求已发送但没有收到响应
      return Promise.reject(new Error('网络连接失败，请检查后端服务是否正常运行'));
    } else {
      // 请求配置出错
      return Promise.reject(new Error('请求配置错误: ' + error.message));
    }
  }
);

/**
 * 获取统计数据
 * @returns {Promise} 统计数据
 */
export const getStats = async () => {
  try {
    const response = await apiClient.get('/stats')
    return response
  } catch (error) {
    console.error('获取统计数据失败:', error)
    
    // 提供更友好的错误信息
    if (error.message.includes('404')) {
      throw new Error('统计数据接口返回404，请先执行 ETL 任务生成数据文件')
    } else if (error.message.includes('Network Error')) {
      throw new Error('网络连接失败，请检查后端服务是否正常运行')
    } else if (error.message.includes('stats not found')) {
      throw new Error('统计数据文件不存在，请先执行 ETL 任务 (run_etl.sh)')
    } else {
      throw new Error('统计数据未生成，请先执行 ETL 任务 (run_etl.sh)')
    }
  }
}

/**
 * 检查后端服务健康状态
 * @returns {Promise} 包含健康状态的Promise
 */
export const checkHealth = async () => {
  try {
    const data = await apiClient.get('/health');
    return data;
  } catch (error) {
    console.error('健康检查失败:', error);
    throw error;
  }
};

export default {
  getStats,
  checkHealth
};