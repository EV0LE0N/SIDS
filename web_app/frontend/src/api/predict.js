import axios from 'axios';

const API_BASE_URL = '/api';

// 创建专门用于文件上传的axios实例
const uploadClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 文件上传需要更长的超时时间
  headers: {
    'Content-Type': 'multipart/form-data',
  }
});

// 请求拦截器
uploadClient.interceptors.request.use(
  config => {
    // 可以在这里添加token等认证信息
    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

// 响应拦截器
uploadClient.interceptors.response.use(
  response => {
    return response.data;
  },
  error => {
    console.error('文件上传请求错误:', error);
    
    // 统一错误处理
    if (error.response) {
      // 服务器返回错误状态码
      const { status, data } = error.response;
      let message = `文件上传失败 (${status})`;
      
      if (data && data.detail) {
        message = data.detail;
      } else if (status === 400) {
        message = '文件格式错误，请上传CSV格式文件';
      } else if (status === 413) {
        message = '文件大小超过限制（最大50MB）';
      } else if (status === 500) {
        message = '服务器处理文件时出错';
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
 * 上传文件进行攻击检测预测
 * @param {FormData} formData 包含文件的FormData对象
 * @returns {Promise} 预测结果
 */
export const uploadPredict = async (formData) => {
  try {
    const response = await uploadClient.post('/predict', formData)
    return response
  } catch (error) {
    console.error('上传预测失败:', error)
    
    // 提供更友好的错误信息
    if (error.message.includes('模型未加载')) {
      throw new Error('检测模型未加载，请先执行模型训练任务')
    } else if (error.message.includes('文件格式')) {
      throw new Error('文件格式错误，请上传CSV或Parquet格式的文件')
    } else if (error.message.includes('413')) {
      throw new Error('文件大小超过限制，请上传小于100MB的文件')
    } else {
      throw error
    }
  }
}

/**
 * 验证文件是否符合要求
 * @param {File} file - 要验证的文件
 * @returns {Object} 验证结果 {valid: boolean, message: string}
 */
export const validateFile = (file) => {
  // 检查文件类型
  const isCSV = file.type === 'text/csv' || file.name.toLowerCase().endsWith('.csv');
  if (!isCSV) {
    return {
      valid: false,
      message: '文件格式错误：只能上传CSV格式文件'
    };
  }
  
  // 检查文件大小（最大50MB）
  const maxSize = 50 * 1024 * 1024; // 50MB
  if (file.size > maxSize) {
    return {
      valid: false,
      message: `文件大小超过限制：${(file.size / 1024 / 1024).toFixed(2)}MB > 50MB`
    };
  }
  
  // 检查文件是否为空
  if (file.size === 0) {
    return {
      valid: false,
      message: '文件为空，请选择有效的CSV文件'
    };
  }
  
  return {
    valid: true,
    message: '文件验证通过'
  };
};

/**
 * 获取文件基本信息
 * @param {File} file - 文件对象
 * @returns {Object} 文件信息 {name: string, size: string, type: string}
 */
export const getFileInfo = (file) => {
  return {
    name: file.name,
    size: formatFileSize(file.size),
    type: file.type || '未知类型',
    lastModified: new Date(file.lastModified).toLocaleString()
  };
};

/**
 * 格式化文件大小
 * @param {number} bytes - 文件大小（字节）
 * @returns {string} 格式化后的文件大小
 */
const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

/**
 * 批量预测（JSON格式）
 * @param {Array} records 记录数组
 * @returns {Promise} 预测结果
 */
export const batchPredict = async (records) => {
  try {
    const response = await uploadClient.post('/predict/batch', { records })
    return response
  } catch (error) {
    console.error('批量预测失败:', error)
    throw error
  }
}

/**
 * 获取模型信息
 * @returns {Promise} 模型信息
 */
export const getModelInfo = async () => {
  try {
    const response = await uploadClient.get('/predict/model-info')
    return response
  } catch (error) {
    console.error('获取模型信息失败:', error)
    throw error
  }
}

export default {
  uploadPredict,
  batchPredict,
  getModelInfo,
  validateFile,
  getFileInfo
}