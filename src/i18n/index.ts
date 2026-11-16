import zh from './zh.json';
import en from './en.json';
import type { Locale } from '../consts';

export const dictionaries = { zh, en } as const;

export type Dict = (typeof dictionaries)[Locale];

export function useDict(locale: Locale): Dict {
  return dictionaries[locale];
}
