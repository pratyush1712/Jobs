/**
 * Route-level loading skeleton shown instantly during navigation
 * while the target page's JS chunk is being fetched.
 */
export default function AppLoading() {
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="h-5 w-5 rounded-full border-2 border-violet border-t-transparent animate-spin" />
    </div>
  );
}
