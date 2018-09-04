import random
import torch.utils.data
import torchvision.transforms as transforms
from base_data_loader import BaseDataLoader
from image_folder import ImageFolder
from builtins import object

class PairedData(object):
    def __init__(self, data_loader_A, data_loader_B, max_dataset_size, flip, opt):
        self.data_loader_A = data_loader_A
        self.data_loader_B = data_loader_B
        self.stop_A = False
        self.stop_B = False
        self.max_dataset_size = max_dataset_size
        self.flip = flip
        self.input_nc = opt.input_nc # rui
        self.output_nc = opt.output_nc # rui

    def __iter__(self):
        self.stop_A = False
        self.stop_B = False
        self.data_loader_A_iter = iter(self.data_loader_A)
        self.data_loader_B_iter = iter(self.data_loader_B)
        self.iter = 0
        return self

    def __next__(self):
        A, A_paths = None, None
        B, B_paths = None, None
        try:
            A, A_paths = next(self.data_loader_A_iter)
        except StopIteration:
            if A is None or A_paths is None:
                self.stop_A = True
                self.data_loader_A_iter = iter(self.data_loader_A)
                A, A_paths = next(self.data_loader_A_iter)

        try:
            B, B_paths = next(self.data_loader_B_iter)
        except StopIteration:
            if B is None or B_paths is None:
                self.stop_B = True
                self.data_loader_B_iter = iter(self.data_loader_B)
                B, B_paths = next(self.data_loader_B_iter)

        if (self.stop_A and self.stop_B) or self.iter > self.max_dataset_size:
            self.stop_A = False
            self.stop_B = False
            raise StopIteration()
        else:
            self.iter += 1
            if self.flip and random.random() < 0.5:
                idx = [i for i in range(A.size(3) - 1, -1, -1)]
                idx = torch.LongTensor(idx)
                A = A.index_select(3, idx)
                B = B.index_select(3, idx)
            # rui add for gray
            if self.input_nc == 1:
                tmp = A[:,0, ...] * 0.299 + A[:,1, ...] * 0.587 + A[:,2, ...] * 0.114
                A = tmp.unsqueeze(1)
            if self.output_nc == 1:
                tmp = B[:,0, ...] * 0.299 + B[:,1, ...] * 0.587 + B[:,2, ...] * 0.114
                B = tmp.unsqueeze(1)
            # rui
            return {'A': A, 'A_paths': A_paths,
                    'B': B, 'B_paths': B_paths}

class UnalignedDataLoader(BaseDataLoader):
    def initialize(self, opt):
        BaseDataLoader.initialize(self, opt)
        transformations = [transforms.Scale(opt.loadSize),
                           transforms.RandomCrop(opt.fineSize),
                           transforms.ToTensor(),
                           transforms.Normalize((0.5, 0.5, 0.5),
                                                (0.5, 0.5, 0.5))]
        transform = transforms.Compose(transformations)

        # Dataset A
        #dataset_A = ImageFolder(root=opt.dataroot + '/' + opt.phase + 'A',
        #                        transform=transform, return_paths=True)
        dataset_A = ImageFolder(root=opt.dataroot + '/' + opt.dataA, # rui
                                transform=transform, return_paths=True)
        data_loader_A = torch.utils.data.DataLoader(
            dataset_A,
            batch_size=self.opt.batchSize,
            shuffle=not self.opt.serial_batches,
            num_workers=int(self.opt.nThreads))

        # Dataset B
        #dataset_B = ImageFolder(root=opt.dataroot + '/' + opt.phase + 'B',
        #                        transform=transform, return_paths=True)
        dataset_B = ImageFolder(root=opt.dataroot + '/' + opt.dataB, # rui
                                transform=transform, return_paths=True)
        data_loader_B = torch.utils.data.DataLoader(
            dataset_B,
            batch_size=self.opt.batchSize,
            shuffle=not self.opt.serial_batches,
            num_workers=int(self.opt.nThreads))
        self.dataset_A = dataset_A
        self.dataset_B = dataset_B
        flip = opt.isTrain and not opt.no_flip
        #self.paired_data = PairedData(data_loader_A, data_loader_B, 
        #                              self.opt.max_dataset_size, flip)
        self.paired_data = PairedData(data_loader_A, data_loader_B, 
                                      self.opt.max_dataset_size, flip, self.opt) # rui

    def name(self):
        return 'UnalignedDataLoader'

    def load_data(self):
        return self.paired_data

    def __len__(self):
        return min(max(len(self.dataset_A), len(self.dataset_B)), self.opt.max_dataset_size)
