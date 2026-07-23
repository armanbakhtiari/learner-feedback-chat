import { Show, SignInButton, SignUpButton } from "@clerk/nextjs";
import Image from "next/image";
import AppShell from "@/components/AppShell";

export default function Home() {
  return (
    <>
      <Show when="signed-out">
        <main className="flex min-h-screen flex-col items-center justify-center gap-6 px-6 text-center">
          <Image src="/sensai_logo.png" alt="SENSAI" width={120} height={120} priority />
          <h1 className="text-3xl font-bold text-slate-800">Agent de rétroaction SENSAI</h1>
          <p className="max-w-md text-slate-600">
            Complétez vos formations par concordance et recevez une rétroaction personnalisée guidée
            par les perspectives d&apos;experts.
          </p>
          <div className="flex gap-3">
            <SignInButton mode="modal">
              <button className="rounded-lg bg-brand px-5 py-2.5 font-medium text-white hover:opacity-90">
                Se connecter
              </button>
            </SignInButton>
            <SignUpButton mode="modal">
              <button className="rounded-lg border border-slate-300 bg-white px-5 py-2.5 font-medium text-slate-700 hover:bg-slate-50">
                Créer un compte
              </button>
            </SignUpButton>
          </div>
        </main>
      </Show>
      <Show when="signed-in">
        <AppShell />
      </Show>
    </>
  );
}
