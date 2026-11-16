import { config, collection, fields } from '@keystatic/core';

/**
 * Keystatic Cloud mode：GitHub App + 登录，生产站保留 /keystatic，账号仅协作者。
 * 内容语言由目录决定（docs/ vs docs-en/），frontmatter 不设 lang。
 */
export default config({
  storage: {
    kind: 'cloud',
  },
  cloud: {
    project: 'Ch1rpys/MirraiSite',
  },
  collections: {
    blog: collection({
      label: '版本博客',
      slugField: 'title',
      path: 'src/content/blog/*',
      format: { contentField: 'content' },
      schema: {
        title: fields.slug({ name: { label: '标题' } }),
        description: fields.text({ label: '描述', validation: { isRequired: true } }),
        order: fields.integer({ label: '排序', defaultValue: 0 }),
        pubDate: fields.date({ label: '发布日期' }),
        content: fields.mdx({ label: '正文' }),
      },
    }),
    docs: collection({
      label: '文档（中文）',
      slugField: 'title',
      path: 'src/content/docs/**',
      format: { contentField: 'content' },
      schema: {
        title: fields.slug({ name: { label: '标题' } }),
        description: fields.text({ label: '描述' }),
        order: fields.integer({ label: '排序', defaultValue: 0 }),
        content: fields.mdx({ label: '正文' }),
      },
    }),
    docsEn: collection({
      label: 'Docs (English)',
      slugField: 'title',
      path: 'src/content/docs-en/**',
      format: { contentField: 'content' },
      schema: {
        title: fields.slug({ name: { label: 'Title' } }),
        description: fields.text({ label: 'Description' }),
        order: fields.integer({ label: 'Order', defaultValue: 0 }),
        content: fields.mdx({ label: 'Body' }),
      },
    }),
  },
});
