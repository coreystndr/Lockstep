export type CatalogItem = { id: string; name: string };

export const agents: CatalogItem[] = [
  { id: "41fb69c1-4189-7b37-f117-bcaf1e96f1bf", name: "Astra" },
  { id: "5f8d3a7f-467b-97f3-062c-13acf203c006", name: "Breach" },
  { id: "9f0d8ba9-4140-b941-57d3-a7ad57c6b417", name: "Brimstone" },
  { id: "22697a3d-45bf-8dd7-4fec-84a9e28c69d7", name: "Chamber" },
  { id: "1dbf2edd-4729-0984-3115-daa5eed44993", name: "Clove" },
  { id: "117ed9e3-49f3-6512-3ccf-0cada7e3823b", name: "Cypher" },
  { id: "cc8b64c8-4b25-4ff9-6e7f-37b4da43d235", name: "Deadlock" },
  { id: "dade69b4-4f5a-8528-247b-219e5a1facd6", name: "Fade" },
  { id: "e370fa57-4757-3604-3648-499e1f642d3f", name: "Gekko" },
  { id: "95b78ed7-4637-86d9-7e41-71ba8c293152", name: "Harbor" },
  { id: "0e38b510-41a8-5780-5e8f-568b2a4f2d6c", name: "Iso" },
  { id: "add6443a-41bd-e414-f6ad-e58d267f4e95", name: "Jett" },
  { id: "601dbbe7-43ce-be57-2a40-4abd24953621", name: "KAY/O" },
  { id: "1e58de9c-4950-5125-93e9-a0aee9f98746", name: "Killjoy" },
  { id: "ddd5a15c-4fbe-42fa-3789-11a55ca5ee04", name: "Hush" },
  { id: "7c8a4701-4de6-9355-b254-e09bc2a34b72", name: "Miks" },
  { id: "bb2a4828-46eb-8cd1-e765-15848195d751", name: "Neon" },
  { id: "8e253930-4c05-31dd-1b6c-968525494517", name: "Omen" },
  { id: "eb93336a-449b-9c1b-0a54-a891f7921d69", name: "Phoenix" },
  { id: "f94c3b30-42be-e959-889c-5aa313dba261", name: "Raze" },
  { id: "a3bfb853-43b2-7238-a4f1-ad90e9e46bcc", name: "Reyna" },
  { id: "569fdd95-4d10-43ab-ca70-79becc718b46", name: "Sage" },
  { id: "6f2a04ca-43e0-be17-7f36-b3908627744d", name: "Skye" },
  { id: "320b2a48-4d9b-a075-30f1-1f93a9b638fa", name: "Sova" },
  { id: "b444168c-4e35-8076-db47-ef9bf368f384", name: "Tejo" },
  { id: "92eeef5d-43b5-1d4a-8d03-b3927a09034b", name: "Veto" },
  { id: "707eab51-4836-f488-046a-cda6bf494859", name: "Viper" },
  { id: "efba5359-4016-a1e5-7626-b1ae76895940", name: "Vyse" },
  { id: "df1cb487-4902-002e-5c17-d28e83e78588", name: "Waylay" },
  { id: "7f94d92c-4234-0a36-9646-3a87eb8b5c89", name: "Yoru" },
];

const mapNames = [
  "Abyss", "Ascent", "Bind", "Breeze", "Corrode", "District", "Drift",
  "Fracture", "Glitch", "Haven", "Icebox", "Kasbah", "Lotus", "Pearl",
  "Piazza", "Split", "Summit", "Sunset", "The Range",
];

export const maps: CatalogItem[] = mapNames.map((name) => ({
  id: name.toLocaleLowerCase("en-US").replace(/[^a-z0-9]+/g, "-"),
  name,
}));
