/**
 * 高德地图 JS API 2.0 动态加载器。
 *
 * Key 只能来自环境变量 VITE_AMAP_KEY（frontend/.env），禁止硬编码。
 * 未配置 Key 或加载失败时 reject，调用方负责降级（隐藏地图，保留文字路线）。
 */

let loadingPromise = null

export function getAmapKey() {
  return String(import.meta.env.VITE_AMAP_KEY || '').trim()
}

export function getAmapSecurityCode() {
  return String(import.meta.env.VITE_AMAP_SECURITY_CODE || '').trim()
}

export function loadAMap() {
  if (typeof window === 'undefined') {
    return Promise.reject(new Error('AMap 只能在浏览器中加载'))
  }
  if (window.AMap) {
    return Promise.resolve(window.AMap)
  }
  const key = getAmapKey()
  if (!key) {
    return Promise.reject(new Error('未配置 VITE_AMAP_KEY'))
  }
  if (loadingPromise) {
    return loadingPromise
  }

  const securityCode = getAmapSecurityCode()
  if (securityCode) {
    window._AMapSecurityConfig = { securityJsCode: securityCode }
  }

  loadingPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    const timer = window.setTimeout(() => {
      cleanup()
      loadingPromise = null
      reject(new Error('AMap SDK 加载超时'))
    }, 10000)

    const cleanup = () => {
      window.clearTimeout(timer)
      script.onload = null
      script.onerror = null
    }

    script.async = true
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${encodeURIComponent(key)}&plugin=AMap.Driving`
    script.onload = () => {
      cleanup()
      if (window.AMap) {
        resolve(window.AMap)
      } else {
        loadingPromise = null
        reject(new Error('AMap SDK 加载异常'))
      }
    }
    script.onerror = () => {
      cleanup()
      loadingPromise = null
      reject(new Error('AMap SDK 加载失败'))
    }
    document.head.appendChild(script)
  })

  return loadingPromise
}
