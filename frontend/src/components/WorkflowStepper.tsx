import { CheckCircle2, Circle, Loader2 } from 'lucide-react';
import type { PlanStatus } from '@/types/api';

interface Step {
  id: PlanStatus[];
  label: string;
  description: string;
}

const STEPS: Step[] = [
  {
    id: ['queued'],
    label: 'Request Received',
    description: 'Your travel request has been submitted.',
  },
  {
    id: ['researching'],
    label: 'Researching Destination',
    description: 'AI agents are gathering insights about your destination.',
  },
  {
    id: ['planning'],
    label: 'Building Itinerary',
    description: 'Creating your personalized day-by-day plan.',
  },
  {
    id: ['awaiting_review', 'revising'],
    label: 'Awaiting Your Review',
    description: 'Your draft itinerary is ready for review.',
  },
  {
    id: ['finalized'],
    label: 'Finalized',
    description: 'Your trip has been approved and is ready!',
  },
];

function getStepIndex(status: PlanStatus): number {
  for (let i = 0; i < STEPS.length; i++) {
    if (STEPS[i].id.includes(status)) return i;
  }
  // Error states — map to last completed
  return 0;
}

type StepState = 'completed' | 'active' | 'upcoming';

function getStepState(stepIndex: number, currentIndex: number): StepState {
  if (stepIndex < currentIndex) return 'completed';
  if (stepIndex === currentIndex) return 'active';
  return 'upcoming';
}

interface WorkflowStepperProps {
  status: PlanStatus;
}

export function WorkflowStepper({ status }: WorkflowStepperProps) {
  const currentIndex = getStepIndex(status);
  const isProcessing = ['researching', 'planning', 'revising', 'queued'].includes(status);

  return (
    <div className="w-full" role="navigation" aria-label="Workflow progress">
      {/* Desktop: horizontal */}
      <div className="hidden md:flex items-start justify-between relative">
        {/* Connector line */}
        <div className="absolute top-4 left-8 right-8 h-px bg-slate-200" aria-hidden="true" />

        {STEPS.map((step, idx) => {
          const state = getStepState(idx, currentIndex);
          const isCurrent = state === 'active';
          const isCompleted = state === 'completed';

          return (
            <div
              key={step.label}
              className="relative flex flex-col items-center flex-1 min-w-0 px-2"
            >
              {/* Step icon */}
              <div
                className={`relative z-10 flex items-center justify-center w-8 h-8 rounded-full border-2 transition-all duration-300 ${
                  isCompleted
                    ? 'bg-brand-600 border-brand-600'
                    : isCurrent
                    ? 'bg-white border-brand-600'
                    : 'bg-white border-slate-200'
                }`}
                aria-current={isCurrent ? 'step' : undefined}
              >
                {isCompleted ? (
                  <CheckCircle2 className="w-4 h-4 text-white" aria-hidden="true" />
                ) : isCurrent && isProcessing ? (
                  <Loader2 className="w-4 h-4 text-brand-600 animate-spin" aria-hidden="true" />
                ) : isCurrent ? (
                  <span className="w-2 h-2 rounded-full bg-brand-600" aria-hidden="true" />
                ) : (
                  <Circle className="w-4 h-4 text-slate-300" aria-hidden="true" />
                )}
              </div>

              {/* Labels */}
              <div className="mt-3 text-center">
                <p
                  className={`text-xs font-semibold leading-tight ${
                    isCompleted || isCurrent ? 'text-slate-800' : 'text-slate-400'
                  }`}
                >
                  {step.label}
                </p>
                {isCurrent && (
                  <p className="text-[11px] text-brand-600 mt-0.5 leading-tight max-w-[120px] mx-auto">
                    {step.description}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Mobile: vertical */}
      <div className="md:hidden space-y-3">
        {STEPS.map((step, idx) => {
          const state = getStepState(idx, currentIndex);
          const isCurrent = state === 'active';
          const isCompleted = state === 'completed';

          return (
            <div key={step.label} className="flex items-start gap-3">
              <div
                className={`flex-shrink-0 flex items-center justify-center w-7 h-7 rounded-full border-2 mt-0.5 ${
                  isCompleted
                    ? 'bg-brand-600 border-brand-600'
                    : isCurrent
                    ? 'bg-white border-brand-600'
                    : 'bg-white border-slate-200'
                }`}
              >
                {isCompleted ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-white" aria-hidden="true" />
                ) : isCurrent && isProcessing ? (
                  <Loader2 className="w-3.5 h-3.5 text-brand-600 animate-spin" aria-hidden="true" />
                ) : isCurrent ? (
                  <span className="w-1.5 h-1.5 rounded-full bg-brand-600" />
                ) : (
                  <span className="w-1.5 h-1.5 rounded-full bg-slate-300" />
                )}
              </div>
              <div>
                <p className={`text-sm font-semibold ${isCompleted || isCurrent ? 'text-slate-800' : 'text-slate-400'}`}>
                  {step.label}
                </p>
                {isCurrent && (
                  <p className="text-xs text-brand-600 mt-0.5">{step.description}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
