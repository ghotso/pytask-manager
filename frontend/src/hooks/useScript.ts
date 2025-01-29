import useSWR from 'swr';
import { Script } from '../types';

const fetcher = async (url: string) => {
  console.log('Fetching from URL:', url);
  const response = await fetch(url);
  
  console.log('Response status:', response.status);
  console.log('Response headers:', Object.fromEntries(response.headers.entries()));
  
  if (!response.ok) {
    console.error('Error response:', {
      status: response.status,
      statusText: response.statusText,
      headers: Object.fromEntries(response.headers.entries()),
    });
    
    try {
      const errorData = await response.json();
      console.error('Error data:', errorData);
      throw new Error(errorData.detail || 'Failed to fetch script');
    } catch (parseError) {
      const textContent = await response.text();
      console.error('Raw error response:', textContent);
      throw new Error(`Failed to fetch script: ${response.statusText}`);
    }
  }
  
  let rawData;
  try {
    const textContent = await response.text();
    console.log('Raw response text:', textContent);
    
    try {
      rawData = JSON.parse(textContent);
      console.log('Parsed response data:', rawData);
    } catch (parseError) {
      console.error('JSON parse error:', parseError);
      console.error('Failed to parse response text:', textContent);
      throw new Error('Invalid JSON response from server');
    }
  } catch (error) {
    console.error('Error reading response:', error);
    throw new Error('Failed to read response from server');
  }
  
  // Validate the response data structure
  if (!rawData || typeof rawData !== 'object') {
    console.error('Invalid data format, received:', rawData);
    throw new Error('Invalid response format');
  }
  
  // Log the shape of the data
  console.log('Data shape:', {
    hasName: 'name' in rawData,
    nameType: typeof rawData.name,
    hasContent: 'content' in rawData,
    contentType: typeof rawData.content,
    hasTags: 'tags' in rawData,
    tagsType: Array.isArray(rawData.tags) ? 'array' : typeof rawData.tags,
    hasDependencies: 'dependencies' in rawData,
    dependenciesType: Array.isArray(rawData.dependencies) ? 'array' : typeof rawData.dependencies,
    hasSchedules: 'schedules' in rawData,
    schedulesType: Array.isArray(rawData.schedules) ? 'array' : typeof rawData.schedules,
  });
  
  // Ensure required fields exist
  if (!rawData.name || typeof rawData.name !== 'string') {
    console.error('Missing or invalid name field:', rawData.name);
    throw new Error('Missing or invalid name field in script data');
  }
  
  if (!rawData.content || typeof rawData.content !== 'string') {
    console.error('Missing or invalid content field:', rawData.content);
    throw new Error('Missing or invalid content field in script data');
  }
  
  // Create validated script object
  const script: Script = {
    ...rawData,
    name: rawData.name,
    content: rawData.content,
    description: rawData.description || '',
    is_active: Boolean(rawData.is_active),
    tags: Array.isArray(rawData.tags) ? rawData.tags : [],
    dependencies: Array.isArray(rawData.dependencies) ? rawData.dependencies : [],
    schedules: Array.isArray(rawData.schedules) ? rawData.schedules : [],
  };
  
  console.log('Validated script object:', script);
  return script;
};

export function useScript(id?: number) {
  const { data, error, mutate } = useSWR<Script>(
    id ? `/api/scripts/${id}` : null,
    fetcher,
    {
      revalidateOnFocus: false,
      shouldRetryOnError: false,
      dedupingInterval: 5000, // Reduce polling frequency
    }
  );
  
  return {
    script: data,
    isLoading: !error && !data,
    error,
    mutate,
  };
} 