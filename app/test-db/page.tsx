import { createClient } from '@supabase/supabase-js';

export default async function TestDB() {
  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );

  const { data, error } = await supabase.from('events').select('count');

  return (
    <div className="p-8">
      <h1 className="text-xl">Database Test</h1>
      {error ? (
        <p className="text-red-500">Error: {error.message}</p>
      ) : (
        <p className="text-green-500">✅ Connected! Table exists.</p>
      )}
    </div>
  );
}