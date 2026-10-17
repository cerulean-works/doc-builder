import { replaceAsync, generateTagRegexWithId, maskCodeBlocks } from "./utils.js";

/**
 * Converts the authored tab syntax into the `Tabs`/`Tab` components:
 *
 *   <hfoptions id="install">            <Tabs id="install" options={["pip", "uv"]}>
 *   <hfoption id="pip">...</hfoption>  →   <Tab id="install" option="pip">...</Tab>
 *   ...                                    ...
 *   </hfoptions>                       </Tabs>
 *
 * `<hfoptions>` is the historical doc-builder syntax; `<tabs>`/`<tab>` is accepted as an alias.
 */
export const tabsPreprocess = {
	markup: async ({ content: source }) => {
		// tab syntax shown inside a code block is an example, not tabs
		const { masked, restore } = maskCodeBlocks(source);
		let content = masked;
		for (const [groupTag, itemTag] of [
			["hfoptions", "hfoption"],
			["tabs", "tab"],
		]) {
			const REGEX_GROUP = generateTagRegexWithId(groupTag, true);
			const REGEX_ITEM = generateTagRegexWithId(itemTag, true);
			content = await replaceAsync(content, REGEX_GROUP, async (_, id, groupContent) => {
				const options = [];
				groupContent = await replaceAsync(
					groupContent,
					REGEX_ITEM,
					async (__, option, itemContent) => {
						options.push(option);
						return `<Tab id="${id}" option="${option}">\n\n${itemContent}\n\n</Tab>`;
					}
				);
				return `<Tabs id="${id}" options={${JSON.stringify(options)}}>\n${groupContent}\n</Tabs>`;
			});
		}
		return { code: restore(content) };
	},
};
