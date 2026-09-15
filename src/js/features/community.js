// Community feed: posts, likes, comments, shares, follows, and the post modal.
import { byId, html, show, hide, delegate, setBusy, setFieldError, clearFormErrors, errorNotice } from '../dom.js';
import { icon } from '../icons.js';
import { api, ApiError } from '../api.js';
import { getIdentity, updateIdentity } from '../state.js';
import { openModal, closeModal, onModalClose } from '../ui/modal.js';
import { notify } from '../ui/toast.js';
import { showSkeleton, skeletonCards, skeletonRows, clearBusy } from '../ui/skeleton.js';
import { bindDropzone, validateImage, compressImage } from '../ui/dropzone.js';
import { onTabShow } from '../nav.js';
import { imageSrc, initials, relativeTime } from '../format.js';
import { debug } from '../env.js';

const els = {};
let posts = [];
let pendingImage = null;
const expanded = new Set();

// Follows are keyed by the author's uid (older posts without one fall back to the name).
const authorKey = (post) => String(post.authorUid || post.username || '');
const isMine = (post) => Boolean(post.mine) || (post.authorUid && post.authorUid === getIdentity().uid);
const isFollowing = (key) => getIdentity().following.includes(key);
let followingSynced = false;

function postCard(post) {
  const id = String(post.id);
  const hashtags = Array.isArray(post.hashtags) ? post.hashtags.filter(Boolean) : [];
  const key = authorKey(post);
  const following = isFollowing(key);
  return html`
    <article class="card" data-post-id="${id}">
      <div class="row">
        <div class="avatar avatar-sm" aria-hidden="true">${initials(post.username)}</div>
        <div class="grow"><p class="list-title">${post.username || 'anonymous'}${isMine(post) ? html` <span class="chip-neutral ml-1">You</span>` : ''}</p><p class="list-text">${relativeTime(post.timestamp) || post.timeAgo || ''}</p></div>
        ${key && !isMine(post) ? html`<button type="button" class="btn-ghost btn-sm" data-action="follow" data-username="${key}" aria-pressed="${following ? 'true' : 'false'}">${following ? 'Following' : 'Follow'}</button>` : ''}
      </div>
      ${post.image ? html`<div class="card-media card-media-square mt-4"><img src="${imageSrc(post.image)}" alt="Post by ${post.username || 'anonymous'}" loading="lazy" width="640" height="640"></div>` : ''}
      ${post.caption ? html`<p class="text-[15px]">${post.caption}</p>` : ''}
      ${hashtags.length ? html`<div class="chip-row mt-2">${hashtags.map((tag) => html`<span class="chip-neutral">#${String(tag).replace(/^#/, '')}</span>`)}</div>` : ''}
      <div class="post-actions">
        <button type="button" class="btn-ghost btn-sm action-button" data-action="like" aria-pressed="${post.liked ? 'true' : 'false'}" aria-label="${post.liked ? 'Unlike' : 'Like'}">${icon('heart')}<span data-count="likes">${Number(post.likes) || 0}</span></button>
        <button type="button" class="btn-ghost btn-sm action-button" data-action="comments" aria-expanded="${expanded.has(id) ? 'true' : 'false'}" aria-label="Comments">${icon('message')}<span data-count="comments">${Number(post.comments) || 0}</span></button>
        <button type="button" class="btn-ghost btn-sm action-button" data-action="share" aria-label="Share">${icon('share')}<span data-count="shares">${Number(post.shares) || 0}</span></button>
      </div>
      <div class="comments ${expanded.has(id) ? '' : 'hidden'}" data-comments></div>
    </article>`;
}

function render() {
  clearBusy(els.feed);
  if (!posts.length) {
    els.feed.innerHTML = '';
    show(els.empty);
    return;
  }
  hide(els.empty);
  els.feed.innerHTML = html`${posts.map(postCard)}`;
  expanded.forEach((id) => { const card = els.feed.querySelector(`[data-post-id="${CSS.escape(id)}"]`); if (card) loadComments(card, id); });
}

async function syncFollowing() {
  if (followingSynced) return;
  try {
    const data = await api.following();
    if (Array.isArray(data.following)) updateIdentity({ following: data.following.map(String) });
    followingSynced = true;
  } catch (err) {
    debug('following sync failed', err);
  }
}

async function loadFeed({ silent = false } = {}) {
  if (!silent) { hide(els.empty); showSkeleton(els.feed, skeletonCards(2)); }
  try {
    await syncFollowing();
    const data = await api.posts();
    posts = Array.isArray(data.posts) ? data.posts : [];
    posts.sort((a, b) => String(b.timestamp || '').localeCompare(String(a.timestamp || '')));
    render();
  } catch (err) {
    debug('feed failed', err);
    clearBusy(els.feed);
    hide(els.empty);
    els.feed.replaceChildren(errorNotice({ title: 'The feed did not load', text: err instanceof ApiError ? err.message : '', onRetry: () => loadFeed() }));
  }
}

function findPost(node) {
  const card = node.closest('[data-post-id]');
  return card ? { card, post: posts.find((p) => String(p.id) === card.dataset.postId) } : { card: null, post: null };
}

async function toggleLike(card, post, button) {
  const wasLiked = Boolean(post.liked);
  post.liked = !wasLiked;
  post.likes = Math.max(0, (Number(post.likes) || 0) + (post.liked ? 1 : -1));
  paintLike(button, post);
  try {
    const data = await api.likePost(post.id);
    if (data && data.success !== false) {
      if (typeof data.liked === 'boolean') post.liked = data.liked;
      if (typeof data.likes === 'number') post.likes = data.likes;
    }
  } catch (err) {
    debug('like failed', err);
    post.liked = wasLiked;
    post.likes = Math.max(0, (Number(post.likes) || 0) + (wasLiked ? 1 : -1));
    notify.error('Could not save your like', err instanceof ApiError ? err.message : '');
  }
  paintLike(button, post);
}

function paintLike(button, post) {
  button.setAttribute('aria-pressed', post.liked ? 'true' : 'false');
  button.setAttribute('aria-label', post.liked ? 'Unlike' : 'Like');
  button.querySelector('[data-count="likes"]').textContent = String(Number(post.likes) || 0);
}

async function loadComments(card, id) {
  const panel = card.querySelector('[data-comments]');
  showSkeleton(panel, skeletonRows(2));
  show(panel);
  try {
    const data = await api.comments(id);
    const comments = Array.isArray(data.comments) ? data.comments : [];
    clearBusy(panel);
    panel.innerHTML = html`
      ${comments.length
        ? comments.map((c) => html`<div class="comment"><span class="comment-author">${c.username || 'anonymous'}</span><span class="comment-text">${c.text}</span></div>`)
        : html`<p class="list-text">No comments yet.</p>`}
      <form class="input-group" data-comment-form>
        <label class="sr-only" for="comment-${id}">Add a comment</label>
        <input type="text" id="comment-${id}" class="input" maxlength="300" placeholder="Add a comment" autocomplete="off">
        <button type="submit" class="btn-secondary">Post</button>
      </form>
      <p class="field-error" data-comment-error hidden></p>`;
  } catch (err) {
    debug('comments failed', err);
    clearBusy(panel);
    panel.replaceChildren(errorNotice({ title: 'Comments did not load', text: err instanceof ApiError ? err.message : '', onRetry: () => loadComments(card, id) }));
  }
}

async function submitComment(form) {
  const { card, post } = findPost(form);
  if (!post) return;
  const input = form.querySelector('input');
  const error = card.querySelector('[data-comment-error]');
  const text = input.value.trim();
  if (!text) { setFieldError(error, 'Write a comment first.', input); return; }
  const button = form.querySelector('button');
  setBusy(button, true);
  try {
    const data = await api.addComment(post.id, { text });
    if (!data || data.success === false) throw new ApiError((data && data.error) || 'The comment was not saved.');
    post.comments = (Number(post.comments) || 0) + 1;
    card.querySelector('[data-count="comments"]').textContent = String(post.comments);
    await loadComments(card, String(post.id));
    card.querySelector('[data-comment-form] input')?.focus();
  } catch (err) {
    debug('comment failed', err);
    setBusy(button, false);
    setFieldError(error, err instanceof ApiError ? err.message : 'The comment could not be posted.');
  }
}

async function share(card, post, button) {
  setBusy(button, true);
  try {
    const data = await api.sharePost(post.id);
    if (!data || data.success === false) throw new ApiError((data && data.error) || 'Could not share the post.');
    post.shares = typeof data.shares === 'number' ? data.shares : (Number(post.shares) || 0) + 1;
    setBusy(button, false);
    button.querySelector('[data-count="shares"]').textContent = String(post.shares);
    notify.info('Post shared', `${post.username ? `${post.username}'s post` : 'The post'} was shared.`);
  } catch (err) {
    debug('share failed', err);
    setBusy(button, false);
    notify.error('Could not share the post', err instanceof ApiError ? err.message : '');
  }
}

async function toggleFollow(button) {
  const username = button.dataset.username;
  const identity = getIdentity();
  const following = identity.following.includes(username);
  setBusy(button, true);
  try {
    const data = following ? await api.unfollow(username) : await api.follow(username);
    if (!data || data.success === false) throw new ApiError((data && data.error) || 'Could not update follow.');
    const next = following ? identity.following.filter((u) => u !== username) : [...identity.following, username];
    updateIdentity({ following: next });
    setBusy(button, false);
    els.feed.querySelectorAll(`[data-action="follow"][data-username="${CSS.escape(username)}"]`).forEach((node) => {
      node.setAttribute('aria-pressed', following ? 'false' : 'true');
      node.textContent = following ? 'Follow' : 'Following';
    });
  } catch (err) {
    debug('follow failed', err);
    setBusy(button, false);
    notify.error('Could not update follow', err instanceof ApiError ? err.message : '');
  }
}

function resetPostForm() {
  pendingImage = null;
  els.input.value = '';
  els.preview.removeAttribute('src');
  hide(els.preview);
  show(els.zone);
  els.caption.value = '';
  clearFormErrors(els.form);
}

async function handleFile(file) {
  clearFormErrors(els.form);
  const problem = validateImage(file);
  if (problem) { setFieldError(els.error, problem); return; }
  try {
    pendingImage = await compressImage(file);
    els.preview.src = pendingImage.dataUrl;
    show(els.preview);
    hide(els.zone);
    els.caption.focus({ preventScroll: true });
  } catch (err) {
    debug('post image failed', err);
    setFieldError(els.error, 'That image could not be read. Try a different file.');
  }
}

async function submitPost(event) {
  event.preventDefault();
  clearFormErrors(els.form);
  if (!pendingImage) { setFieldError(els.error, 'Choose a photo to post.'); els.input.focus(); return; }
  const caption = els.caption.value.trim();
  const hashtags = Array.from(caption.matchAll(/#([\p{L}\p{N}_]+)/gu), (m) => m[1]);
  setBusy(els.submit, true, 'Posting…');
  try {
    // The author is the signed-in account; the server ignores any username sent.
    const data = await api.createPost({ image: pendingImage.base64, caption, hashtags });
    if (!data || data.success === false) throw new ApiError((data && (data.reason || data.error)) || 'The post was not saved.');
    closeModal('add-post-modal');
    notify.success('Posted', 'Your cut is on the feed.');
    await loadFeed({ silent: true });
  } catch (err) {
    debug('post failed', err);
    const message = err instanceof ApiError ? (err.data && err.data.reason) || err.message : 'The post could not be shared.';
    setFieldError(els.error, message);
  } finally {
    setBusy(els.submit, false);
  }
}

export function initCommunity() {
  Object.assign(els, {
    feed: byId('social-feed-container'),
    empty: byId('feed-empty'),
    form: byId('post-form'),
    input: byId('post-image-input'),
    zone: byId('post-image-area'),
    preview: byId('post-image-preview'),
    caption: byId('post-caption'),
    error: byId('post-error'),
    submit: byId('submit-post'),
  });
  byId('add-post-button').addEventListener('click', () => { resetPostForm(); openModal('add-post-modal'); });
  bindDropzone({ input: els.input, zone: els.zone, onFile: handleFile });
  els.form.addEventListener('submit', submitPost);
  onModalClose('add-post-modal', resetPostForm);

  delegate(els.feed, 'click', '[data-action]', (event, button) => {
    const { card, post } = findPost(button);
    const action = button.dataset.action;
    if (action === 'follow') { toggleFollow(button); return; }
    if (!post) return;
    if (action === 'like') toggleLike(card, post, button);
    else if (action === 'share') share(card, post, button);
    else if (action === 'comments') {
      const id = String(post.id);
      if (expanded.has(id)) { expanded.delete(id); hide(card.querySelector('[data-comments]')); button.setAttribute('aria-expanded', 'false'); }
      else { expanded.add(id); button.setAttribute('aria-expanded', 'true'); loadComments(card, id); }
    }
  });
  els.feed.addEventListener('submit', (event) => {
    const form = event.target.closest('[data-comment-form]');
    if (!form) return;
    event.preventDefault();
    submitComment(form);
  });
  onTabShow('community', () => loadFeed({ silent: posts.length > 0 }));
}
