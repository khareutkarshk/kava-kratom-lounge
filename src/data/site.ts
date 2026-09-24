/**
 * Site content for The Batcave — document-derived strings only.
 */
import content from './site-content.json';

export type SiteContent = typeof content;
export const site = content as SiteContent;
export default site;
