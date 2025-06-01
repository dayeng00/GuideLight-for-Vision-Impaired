/**
 * 应用配置文件
 */

// 高德地图配置
export const MAP_CONFIG = {
  key: 'ab13332a406ab60a3c18126b26eeb9c4',  // 高德地图API密钥
  securityJsCode: 'ddd0878499346690f2684a28c4992aed',  // 高德地图安全密钥
  version: '2.0',
  plugins: 'AMap.Scale,AMap.ToolBar,AMap.MapType,AMap.Buildings'
}

// 系统配置
export const SYSTEM_CONFIG = {
  apiBaseUrl: '/',
  apiTimeout: 10000
}

export default {
  MAP_CONFIG,
  SYSTEM_CONFIG
} 