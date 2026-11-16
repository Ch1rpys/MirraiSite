import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

/** 创作手记（MDX）：语言由文件名决定（zh.mdx / en.mdx），frontmatter 不设 lang */
const handnotes = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/handnotes' }),
  schema: z.object({
    title: z.string(),
    description: z.string().optional(),
    order: z.number().default(0),
  }),
});

/** 版本博客 */
const blog = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/blog' }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    order: z.number().default(0),
    pubDate: z.coerce.date(),
  }),
});

/** 版本博客（en） */
const blogEn = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/blog-en' }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    order: z.number().default(0),
    pubDate: z.coerce.date(),
  }),
});

/** 文档（zh）—— 语言由目录决定 */
const docs = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/docs' }),
  schema: z.object({
    title: z.string(),
    description: z.string().optional(),
    order: z.number().default(0),
  }),
});

/** 文档（en） */
const docsEn = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/docs-en' }),
  schema: z.object({
    title: z.string(),
    description: z.string().optional(),
    order: z.number().default(0),
  }),
});

export const collections = { handnotes, blog, blogEn, docs, docsEn };
