import api from './index'

export function getAdminPostList(params) {
  return api.get('/api/v1/admin/post/list', { params })
}

export function reviewPost(postId, status) {
  return api.put(`/api/v1/admin/post/${postId}/review`, { status })
}

export function getAdminCommentList(params) {
  return api.get('/api/v1/admin/comment/list', { params })
}

export function reviewComment(commentId, status) {
  return api.put(`/api/v1/admin/comment/${commentId}/review`, { status })
}
