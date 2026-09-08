import { Redirect } from "expo-router";

export default function ProposalsScreen() {
  return <Redirect href={{ pathname: "/assistant", params: { section: "proposals" } }} />;
}
