import api from './index'

export function createComment(postId, data) {
  return api.post('/api/v1/comment', data, { params: { post_id: postId } })
}

export function deleteComment(commentId) {
  return api.delete(`/api/v1/comment/${commentId}`)
}
