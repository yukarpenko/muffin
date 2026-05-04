import numpy as np
import argparse
import os
import sys
import shutil

spectators = []  ## list of lists of spectators, in all events


def read_spectators():
 """Read all spectator configurations (events) from --spectator_list into the module-level `spectators`
 list. Returns the number of events parsed; an event counts whether or not
 it contains any spectator-particle lines (so consecutive `#event` markers
 representing events with zero spectator nucleons are still counted as
 separate events with multiplicity 0).

 The caller is responsible for verifying that the file exists before calling
 this function.

 NOTE: the count is *returned* (not stored in a module-level variable)
 to avoid the local-vs-global shadowing pitfall that previously caused
 spectator_events to silently stay at 0."""
 count = 0
 buff = []
 in_event = False  # True after we have seen the first `#event` header
 with open(args.spectator_list, 'r') as fspec:
  for line in fspec:
   if(len(line.split()) == 12):
    buff.append(line)
   if(line.startswith('#event')): # catches the # event X out Y lines
    if in_event:
     # Flush the previous event. Its multiplicity may be 0 if the file
     # contained two consecutive `#event` markers with no data lines
     # between them -- that still counts as a spectator event.
     print('int. spectator count: ', count, '  mult ', len(buff))
     spectators.append(buff)
     count = count + 1
     buff = []
    in_event = True
 # Flush the last event if we were inside one (regardless of multiplicity).
 # This also handles the case where the file ends without a trailing
 # `#event` marker.
 if in_event:
  print('int. spectator count: ', count, '  mult ', len(buff))
  spectators.append(buff)
  count = count + 1
 return count


def read_sampler_output_and_write_full_output(spectator_events):
 """Stream the sampler file, merge each sampler event with the corresponding
 spectator event (cycling through the spectator pool when it is shorter than
 the sampler list), and write the merged stream to --output.

 Spectator events with 0 nucleons are handled transparently: an empty
 spectator-line block contributes nothing to the merged event, and the
 `out N` count in the OSCAR header reflects only the sampled hadrons.

 Sampler events are counted on the fly here, removing the need for a
 separate first pass over the (potentially very large) sampler file.

 Returns the number of sampler events processed."""
 buff = []
 event_count = 0
 spectator_event_count = 0
 max_id = 0
 wrap_around_announced = False
 with open(args.sampled_particle_list, 'r') as f, open(args.output, 'w') as fout:
  for line in f:
   if(line.startswith('#!OSCAR2013') or line.startswith('# Units') or line.startswith('# SMASH')):
    fout.write(line)
   if(len(line.split()) == 12):
    buff.append(line)
    max_id = max(max_id, int(line.split()[10]))
   if(line.startswith('# event') and line.split()[3] == 'end'): # catches the # event X end ... lines
    print(line)
    print('int. event count: ', event_count, '  mult ', len(buff))
    print('max_id: ', max_id)
    n_spec = len(spectators[spectator_event_count])
    fout.write('# event ' + str(event_count) + ' out ' + str(len(buff)+n_spec) + '\n')
    fout.write(''.join(buff))  ## write the sampled hadrons
    fout.write(''.join(spectators[spectator_event_count]))  ## add the spectators (may be empty)
    fout.write('# event ' + str(event_count) + ' end 0 impact   0.000 scattering_projectile_target yes\n')
    event_count = event_count + 1
    spectator_event_count = spectator_event_count + 1
    if(spectator_event_count >= spectator_events):
     spectator_event_count = 0
     if not wrap_around_announced:
      print('add_spectators.py:  spectator pool exhausted after sampler event',
            event_count - 1, '; wrapping back to spectator event 0.')
      wrap_around_announced = True
    buff = []
    max_id = 0
 return event_count


if __name__ == '__main__':
 parser = argparse.ArgumentParser()
 parser.add_argument("--sampled_particle_list", required = True,
                     help="File containing the sampled particle lists.")
 parser.add_argument("--spectator_list", required = True,
                     help="File containing the spectator lists.")
 parser.add_argument("--output", required = True,
                     help="output")
 args = parser.parse_args()

 # Hard-fail only when the spectator file is missing entirely. A spectator
 # file that exists but contains events with zero spectator nucleons
 # (or even a file with no parseable events at all) is a legitimate input
 # and is handled below.
 if not os.path.exists(args.spectator_list):
  sys.exit('add_spectators.py:  ERROR: spectator file ' + args.spectator_list
           + ' not found; aborting.')

 spectator_events = read_spectators()
 print('length of spectator meta-array: ', len(spectators))

 if spectator_events == 0:
  # File existed but contained no `#event` markers at all, so there is
  # nothing to merge.  Pass the sampler file through unchanged so the
  # rest of the pipeline still has a well-formed OSCAR input.  This is
  # intentionally distinct from the "file not found" case above, which
  # is a hard error.
  print('add_spectators.py:  WARNING: spectator file ' + args.spectator_list
        + ' contains no events; passing sampled hadrons to output '
        'without adding any spectators.')
  shutil.copy(args.sampled_particle_list, args.output)
 else:
  print('add_spectators.py:  merging spectators and sampled hadrons...')
  sampler_events = read_sampler_output_and_write_full_output(spectator_events)
  if spectator_events < sampler_events:
   print('add_spectators.py:  reused', spectator_events,
         'spectator events to cover', sampler_events, 'sampler events.')
  else:
   print('add_spectators.py:  merged', sampler_events, 'sampler events with',
         spectator_events, 'spectator events available (no reuse needed).')
