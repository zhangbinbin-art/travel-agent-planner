import api from './index'

export function getPostList(params) {
  return api.get('/api/v1/post/list', { params })
}

export function getPostDetail(id) {
  return api.get(`/api/v1/post/${id}`)
}

export function createPost(data) {
  return api.post('/api/v1/post', data)
}

export function updatePost(id, data) {
  return api.put(`/api/v1/post/${id}`, data)
}

export function deletePost(id) {
  return api.delete(`/api/v1/post/${id}`)
}
