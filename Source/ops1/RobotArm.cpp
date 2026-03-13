#include "RobotArm.h"

ARobotArm::ARobotArm(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer)
{
    PrimaryActorTick.bCanEverTick = true;
    GraspComponent = ObjectInitializer.CreateDefaultSubobject<UGraspComponent>(this, TEXT("GraspComponent"));
    RootComponent = GraspComponent;
}

void ARobotArm::BeginPlay()
{
    Super::BeginPlay();
}

void ARobotArm::Tick(float DeltaTime)
{
    Super::Tick(DeltaTime);
}

void ARobotArm::ExecuteTrial(AActor* TargetObject, FVector PlacementTarget)
{
    GraspComponent->BeginGraspSequence(TargetObject, PlacementTarget);
}

bool ARobotArm::IsTrialComplete() const
{
    return GraspComponent->IsSequenceComplete();
}

void ARobotArm::ResetForNextTrial()
{
    GraspComponent->ResetState();
}