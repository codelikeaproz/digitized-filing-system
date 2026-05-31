export type AssistantPageContext = {
  folderId?: string;
  folderName?: string;
  categoryId?: string;
  categoryName?: string;
};

export function resolvePageContextQuery(query: string, context?: AssistantPageContext | null) {
  if (!context?.folderName && !context?.categoryName) {
    return query;
  }

  let result = query;
  const normalized = query.trim().toLowerCase();
  const mentionsDocuments =
    /\b(document|documents|file|files|record|records)\b/i.test(normalized) ||
    /\b(list|show|all|how many|count)\b/i.test(normalized);

  if (context.folderName) {
    const folder = context.folderName;
    const folderReplacements: Array<[RegExp, string]> = [
      [/\bthis folder\b/gi, `${folder} folder`],
      [/\bthe current folder\b/gi, `${folder} folder`],
      [/\bcurrent folder\b/gi, `${folder} folder`],
      [/\bin this folder\b/gi, `in ${folder} folder`],
      [/\bin the current folder\b/gi, `in ${folder} folder`],
      [/\ball files in this folder\b/gi, `all files in ${folder} folder`],
      [/\bshow all documents here\b/gi, `show all documents in ${folder} folder`],
      [/\blist everything in the current folder\b/gi, `list all documents in ${folder} folder`],
    ];
    for (const [pattern, replacement] of folderReplacements) {
      result = result.replace(pattern, replacement);
    }
    if (mentionsDocuments) {
      result = result.replace(/\bin here\b/gi, `in ${folder} folder`);
      result = result.replace(/\bhere\b/gi, `in ${folder} folder`);
    }
  }

  if (context.categoryName) {
    const category = context.categoryName;
    const categoryReplacements: Array<[RegExp, string]> = [
      [/\bthis category\b/gi, `${category} category`],
      [/\bthe current category\b/gi, `${category} category`],
      [/\bcurrent category\b/gi, `${category} category`],
      [/\bin this category\b/gi, `in ${category} category`],
    ];
    for (const [pattern, replacement] of categoryReplacements) {
      result = result.replace(pattern, replacement);
    }
  }

  return result;
}

export function formatAssistantPageContextLabel(context?: AssistantPageContext | null) {
  if (!context) return null;
  const parts: string[] = [];
  if (context.folderName) parts.push(`Folder: ${context.folderName}`);
  if (context.categoryName) parts.push(`Category: ${context.categoryName}`);
  return parts.length ? parts.join(" · ") : null;
}
