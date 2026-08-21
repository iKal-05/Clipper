import { useState } from 'react';
import { type Job } from '../lib/api';
import JobForm from '../components/JobForm';
import ProgressPanel from '../components/ProgressPanel';

export default function HomePage() {
  const [job, setJob] = useState<Job | null>(null);
  const [view, setView] = useState<'form' | 'progress'>('form');

  function handleJobCreated(newJob: Job) {
    setJob(newJob);
    setView('progress');
  }

  function handleDone() {
    if (job) {
      window.location.href = `/job/${job.id}`;
    }
  }

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 py-12 px-4">
      <div className="max-w-3xl mx-auto">
        <header className="text-center mb-12">
          <h1 className="text-4xl font-bold tracking-tight mb-2">Clipper</h1>
          <p className="text-neutral-400">YouTube → Vertical Shorts</p>
        </header>

        {view === 'form' ? (
          <JobForm onSubmit={handleJobCreated} />
        ) : job ? (
          <ProgressPanel jobId={job.id} onDone={handleDone} />
        ) : null}
      </div>
    </div>
  );
}