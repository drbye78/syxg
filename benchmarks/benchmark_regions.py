"""
Performance Benchmarks for Region-Based Architecture

Benchmarks for:
- Region creation time
- Sample generation throughput
- Memory usage
- CPU usage per region type
"""

import sys
import time
sys.path.insert(0, '/mnt/c/work/guga/syxg')

import numpy as np
from typing import Dict, Any, List

from synth.engine.region_descriptor import RegionDescriptor
from synth.partial.wavetable_region import WavetableRegion
from synth.partial.additive_region import AdditiveRegion
from synth.partial.physical_region import PhysicalRegion
from synth.partial.granular_region import GranularRegion
from synth.partial.fdsp_region import FDSPRegion
from synth.partial.an_region import ANRegion


class RegionBenchmark:
    """Benchmark suite for region implementations."""
    
    def __init__(self, sample_rate: int = 44100, block_size: int = 1024):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.results: Dict[str, Dict[str, float]] = {}
    
    def benchmark_region_creation(
        self, 
        region_class: type, 
        descriptor: RegionDescriptor,
        iterations: int = 100
    ) -> Dict[str, float]:
        """
        Benchmark region creation time.
        
        Args:
            region_class: Region class to benchmark
            descriptor: Region descriptor
            iterations: Number of iterations
        
        Returns:
            Dictionary with timing statistics
        """
        times = []
        
        for _ in range(iterations):
            start = time.perf_counter()
            region = region_class(descriptor, self.sample_rate)
            elapsed = time.perf_counter() - start
            times.append(elapsed)
        
        return {
            'min_ms': min(times) * 1000,
            'max_ms': max(times) * 1000,
            'avg_ms': np.mean(times) * 1000,
            'std_ms': np.std(times) * 1000,
            'total_ms': sum(times) * 1000,
            'iterations': iterations
        }
    
    def benchmark_sample_generation(
        self,
        region: Any,
        iterations: int = 100
    ) -> Dict[str, float]:
        """
        Benchmark sample generation throughput.
        
        Args:
            region: Region instance
            iterations: Number of iterations
        
        Returns:
            Dictionary with throughput statistics
        """
        times = []
        total_samples = 0
        
        modulation = {}
        
        for _ in range(iterations):
            start = time.perf_counter()
            samples = region.generate_samples(self.block_size, modulation)
            elapsed = time.perf_counter() - start
            times.append(elapsed)
            total_samples += len(samples)
        
        total_time = sum(times)
        
        return {
            'samples_per_second': total_samples / total_time if total_time > 0 else 0,
            'ms_per_block': (total_time / iterations) * 1000,
            'cpu_load_percent': (total_time / (iterations * self.block_size / self.sample_rate)) * 100,
            'total_samples': total_samples,
            'total_time_ms': total_time * 1000
        }
    
    def run_all_benchmarks(self) -> Dict[str, Any]:
        """
        Run all benchmarks for all region types.
        
        Returns:
            Dictionary with all benchmark results
        """
        results = {}
        
        # WavetableRegion benchmarks
        print("Benchmarking WavetableRegion...")
        wt_descriptor = RegionDescriptor(
            region_id=0,
            engine_type='wavetable',
            key_range=(0, 127),
            velocity_range=(0, 127),
            algorithm_params={
                'wavetable': 'default',
                'unison_voices': 4,
                'detune_amount': 10.0
            }
        )
        
        wt_creation = self.benchmark_region_creation(WavetableRegion, wt_descriptor)
        results['WavetableRegion'] = {'creation': wt_creation}
        
        wt_region = WavetableRegion(wt_descriptor, self.sample_rate)
        wt_region.note_on(100, 60)
        wt_generation = self.benchmark_sample_generation(wt_region)
        results['WavetableRegion']['generation'] = wt_generation
        
        # AdditiveRegion benchmarks
        print("Benchmarking AdditiveRegion...")
        add_descriptor = RegionDescriptor(
            region_id=0,
            engine_type='additive',
            key_range=(0, 127),
            velocity_range=(0, 127),
            algorithm_params={
                'spectrum_type': 'sawtooth',
                'max_partials': 64
            }
        )
        
        add_creation = self.benchmark_region_creation(AdditiveRegion, add_descriptor)
        results['AdditiveRegion'] = {'creation': add_creation}
        
        add_region = AdditiveRegion(add_descriptor, self.sample_rate)
        add_region.note_on(100, 60)
        add_generation = self.benchmark_sample_generation(add_region)
        results['AdditiveRegion']['generation'] = add_generation
        
        # PhysicalRegion benchmarks
        print("Benchmarking PhysicalRegion...")
        phys_descriptor = RegionDescriptor(
            region_id=0,
            engine_type='physical',
            key_range=(0, 127),
            velocity_range=(0, 127),
            algorithm_params={
                'model_type': 'string',
                'excitation_type': 'pluck'
            }
        )
        
        phys_creation = self.benchmark_region_creation(PhysicalRegion, phys_descriptor)
        results['PhysicalRegion'] = {'creation': phys_creation}
        
        phys_region = PhysicalRegion(phys_descriptor, self.sample_rate)
        phys_region.note_on(100, 60)
        phys_generation = self.benchmark_sample_generation(phys_region)
        results['PhysicalRegion']['generation'] = phys_generation
        
        # GranularRegion benchmarks
        print("Benchmarking GranularRegion...")
        gran_descriptor = RegionDescriptor(
            region_id=0,
            engine_type='granular',
            key_range=(0, 127),
            velocity_range=(0, 127),
            algorithm_params={
                'max_clouds': 4,
                'density': 10.0
            }
        )
        
        gran_creation = self.benchmark_region_creation(GranularRegion, gran_descriptor)
        results['GranularRegion'] = {'creation': gran_creation}
        
        gran_region = GranularRegion(gran_descriptor, self.sample_rate)
        gran_region.note_on(100, 60)
        gran_generation = self.benchmark_sample_generation(gran_region)
        results['GranularRegion']['generation'] = gran_generation
        
        # FDSPRegion benchmarks
        print("Benchmarking FDSPRegion...")
        fdsp_descriptor = RegionDescriptor(
            region_id=0,
            engine_type='fdsp',
            key_range=(0, 127),
            velocity_range=(0, 127),
            algorithm_params={
                'phoneme': 'a',
                'excitation_type': 'vocal'
            }
        )
        
        fdsp_creation = self.benchmark_region_creation(FDSPRegion, fdsp_descriptor)
        results['FDSPRegion'] = {'creation': fdsp_creation}
        
        fdsp_region = FDSPRegion(fdsp_descriptor, self.sample_rate)
        fdsp_region.note_on(100, 60)
        fdsp_generation = self.benchmark_sample_generation(fdsp_region)
        results['FDSPRegion']['generation'] = fdsp_generation
        
        # ANRegion benchmarks
        print("Benchmarking ANRegion...")
        an_descriptor = RegionDescriptor(
            region_id=0,
            engine_type='an',
            key_range=(0, 127),
            velocity_range=(0, 127),
            algorithm_params={
                'model_type': 'string',
                'exciter_type': 'pluck'
            }
        )
        
        an_creation = self.benchmark_region_creation(ANRegion, an_descriptor)
        results['ANRegion'] = {'creation': an_creation}
        
        an_region = ANRegion(an_descriptor, self.sample_rate)
        an_region.note_on(100, 60)
        an_generation = self.benchmark_sample_generation(an_region)
        results['ANRegion']['generation'] = an_generation
        
        self.results = results
        return results
    
    def print_results(self) -> None:
        """Print benchmark results in formatted table."""
        print("\n" + "=" * 80)
        print("REGION BENCHMARK RESULTS")
        print("=" * 80)
        
        print("\n--- Region Creation Time (ms) ---")
        print(f"{'Region Type':<25} {'Min':<10} {'Max':<10} {'Avg':<10} {'Std':<10}")
        print("-" * 65)
        
        for region_type, data in self.results.items():
            creation = data.get('creation', {})
            print(f"{region_type:<25} "
                  f"{creation.get('min_ms', 0):<10.3f} "
                  f"{creation.get('max_ms', 0):<10.3f} "
                  f"{creation.get('avg_ms', 0):<10.3f} "
                  f"{creation.get('std_ms', 0):<10.3f}")
        
        print("\n--- Sample Generation Throughput ---")
        print(f"{'Region Type':<25} {'Samples/s':<15} {'ms/block':<12} {'CPU %':<10}")
        print("-" * 62)
        
        for region_type, data in self.results.items():
            generation = data.get('generation', {})
            print(f"{region_type:<25} "
                  f"{generation.get('samples_per_second', 0):<15.0f} "
                  f"{generation.get('ms_per_block', 0):<12.3f} "
                  f"{generation.get('cpu_load_percent', 0):<10.1f}")
        
        print("\n" + "=" * 80)
        
        # Summary statistics
        print("\n--- Summary ---")
        all_creation_times = [
            data['creation']['avg_ms'] 
            for data in self.results.values() 
            if 'creation' in data
        ]
        all_cpu_loads = [
            data['generation']['cpu_load_percent']
            for data in self.results.values()
            if 'generation' in data
        ]
        
        if all_creation_times:
            print(f"Average region creation time: {np.mean(all_creation_times):.3f} ms")
            print(f"Fastest region creation: {min(all_creation_times):.3f} ms")
            print(f"Slowest region creation: {max(all_creation_times):.3f} ms")
        
        if all_cpu_loads:
            print(f"Average CPU load: {np.mean(all_cpu_loads):.1f}%")
            print(f"Max CPU load: {max(all_cpu_loads):.1f}%")
        
        print("=" * 80)


def run_benchmarks():
    """Run all benchmarks and print results."""
    benchmark = RegionBenchmark(sample_rate=44100, block_size=1024)
    results = benchmark.run_all_benchmarks()
    benchmark.print_results()
    return results


if __name__ == '__main__':
    run_benchmarks()
