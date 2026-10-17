import { writable } from "svelte/store";

// used by Tabs.svelte / Tab.svelte: the selected option of every tab group, keyed by group id
export const selectedTabs = writable<Record<string, string>>({});
