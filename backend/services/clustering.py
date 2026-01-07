"""
Face clustering using HDBSCAN.
Groups similar face embeddings into person clusters.
"""

import numpy as np
from sklearn.preprocessing import normalize
import hdbscan


class FaceClusterer:
    """
    Cluster face embeddings using HDBSCAN algorithm.
    HDBSCAN is ideal because:
    - Doesn't require specifying number of clusters
    - Handles varying cluster sizes well
    - Automatically identifies outliers (noise)
    """
    
    def __init__(
        self,
        min_cluster_size: int = 3,
        min_samples: int = 2,
        cluster_selection_epsilon: float = 0.3,
    ):
        """
        Initialize the clusterer.
        
        Args:
            min_cluster_size: Minimum photos needed to form a "person" cluster.
                             Set to 3 so single appearances are marked as rare.
            min_samples: Core point neighborhood size. Lower = more clusters.
            cluster_selection_epsilon: Distance threshold for cluster formation.
        """
        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples
        self.cluster_selection_epsilon = cluster_selection_epsilon
        self.clusterer = None
        self.labels_ = None
    
    def fit(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Cluster face embeddings.
        
        Args:
            embeddings: Array of face embeddings [N, 512]
            
        Returns:
            Array of cluster labels [N]. -1 indicates noise/outlier.
        """
        if len(embeddings) == 0:
            return np.array([])
        
        # Normalize embeddings (should already be normalized, but ensure it)
        embeddings = normalize(embeddings)
        
        # Use cosine distance (1 - cosine_similarity)
        # HDBSCAN works better with Euclidean on normalized vectors
        # (which is equivalent to angular distance)
        self.clusterer = hdbscan.HDBSCAN(
            min_cluster_size=self.min_cluster_size,
            min_samples=self.min_samples,
            cluster_selection_epsilon=self.cluster_selection_epsilon,
            metric='euclidean',  # On normalized vectors, euclidean ~ angular
            cluster_selection_method='eom',  # Excess of Mass
            prediction_data=True,  # Enable soft clustering
        )
        
        self.labels_ = self.clusterer.fit_predict(embeddings)
        
        return self.labels_
    
    def get_cluster_info(self) -> dict:
        """
        Get information about the clustering results.
        
        Returns:
            Dictionary with cluster statistics
        """
        if self.labels_ is None:
            return {}
        
        unique_labels = np.unique(self.labels_)
        n_clusters = len(unique_labels[unique_labels >= 0])
        n_noise = np.sum(self.labels_ == -1)
        
        cluster_sizes = {}
        for label in unique_labels:
            if label >= 0:
                cluster_sizes[int(label)] = int(np.sum(self.labels_ == label))
        
        return {
            'n_clusters': n_clusters,
            'n_noise': n_noise,
            'n_total': len(self.labels_),
            'cluster_sizes': cluster_sizes,
        }
    
    def predict_cluster(self, embedding: np.ndarray, embeddings: np.ndarray) -> int:
        """
        Predict which cluster a new embedding belongs to.
        Uses nearest neighbor matching.
        
        Args:
            embedding: Single face embedding [512]
            embeddings: All embeddings used for clustering [N, 512]
            
        Returns:
            Cluster label or -1 if no match
        """
        if self.labels_ is None or len(embeddings) == 0:
            return -1
        
        # Normalize
        embedding = embedding / np.linalg.norm(embedding)
        embeddings = normalize(embeddings)
        
        # Find nearest neighbor
        similarities = np.dot(embeddings, embedding)
        best_idx = np.argmax(similarities)
        best_sim = similarities[best_idx]
        
        # Threshold for matching
        if best_sim > 0.5:  # ~60 degree angle
            return int(self.labels_[best_idx])
        
        return -1
    
    def merge_clusters(self, labels: np.ndarray, cluster_a: int, cluster_b: int) -> np.ndarray:
        """
        Merge two clusters into one.
        
        Args:
            labels: Current cluster labels
            cluster_a: First cluster to merge
            cluster_b: Second cluster to merge (will be merged into cluster_a)
            
        Returns:
            Updated cluster labels
        """
        labels = labels.copy()
        labels[labels == cluster_b] = cluster_a
        return labels
    
    def recluster_subset(
        self,
        embeddings: np.ndarray,
        indices: list[int],
        min_cluster_size: int = 2
    ) -> np.ndarray:
        """
        Re-cluster a subset of embeddings. Useful for splitting incorrectly
        merged clusters.
        
        Args:
            embeddings: All embeddings
            indices: Indices of embeddings to re-cluster
            min_cluster_size: Minimum cluster size for sub-clustering
            
        Returns:
            New labels for the subset
        """
        subset = embeddings[indices]
        
        sub_clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=1,
            metric='euclidean',
        )
        
        return sub_clusterer.fit_predict(normalize(subset))


def cluster_faces(
    embeddings: np.ndarray,
    min_photos_per_person: int = 3
) -> tuple[np.ndarray, dict]:
    """
    Convenience function to cluster face embeddings.
    
    Args:
        embeddings: Face embeddings array [N, 512]
        min_photos_per_person: Minimum photos to form a person cluster
        
    Returns:
        Tuple of (labels, cluster_info)
    """
    clusterer = FaceClusterer(min_cluster_size=min_photos_per_person)
    labels = clusterer.fit(embeddings)
    info = clusterer.get_cluster_info()
    
    return labels, info
