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

export function likePost(id) {
  return api.post(`/api/v1/post/${id}/like`)
}

export function createPostComment(postId, data) {
  return api.post(`/api/v1/post/${postId}/comment`, data)
}

export function getCommentList(postId, params) {
  return api.get(`/api/v1/post/${postId}/comment-list`, { params })
}

export function getSpotSentiment(spotId) {
  return api.get(`/api/v1/post/spot/${spotId}/sentiment`)
}
